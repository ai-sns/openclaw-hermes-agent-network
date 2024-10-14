import os
import sys
import threading
from collections import deque
from typing import Dict, List, Optional, Any
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QLineEdit, QPushButton, QVBoxLayout, QWidget
from langchain import LLMChain, OpenAI, PromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import BaseLLM
from langchain.vectorstores.base import VectorStore
from pydantic import BaseModel, Field
from langchain.chains.base import Chain
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from langchain.utilities import SerpAPIWrapper

os.environ["OPENAI_API_KEY"] = "sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t"
os.environ["SERPAPI_API_KEY"] = "687b06bb7a85a498782714713b58dfb46369b97093fc6d24d261c6589e8b9c89"

# Define your embedding model
embeddings_model = OpenAIEmbeddings()

# Initialize the vectorstore as empty
import faiss

embedding_size = 1536
index = faiss.IndexFlatL2(embedding_size)
vectorstore = FAISS(embeddings_model.embed_query, index, InMemoryDocstore({}), {})

class TaskCreationChain(LLMChain):
    """Chain to generate tasks."""
    @classmethod
    def from_llm(cls, llm: BaseLLM, verbose: bool = True) -> LLMChain:
        task_creation_template = (
            "You are a task creation AI that uses the result of an execution agent "
            "to create new tasks with the following objective: {objective}, "
            "The last completed task has the result: {result}. "
            "This result was based on this task description: {task_description}. "
            "These are incomplete tasks: {incomplete_tasks}. "
            "Based on the result, create new tasks to be completed "
            "by the AI system that do not overlap with incomplete tasks. "
            "Return the tasks as an array."
        )
        prompt = PromptTemplate(
            template=task_creation_template,
            input_variables=["result", "task_description", "incomplete_tasks", "objective"],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)

class TaskPrioritizationChain(LLMChain):
    """Chain to prioritize tasks."""
    @classmethod
    def from_llm(cls, llm: BaseLLM, verbose: bool = True) -> LLMChain:
        task_prioritization_template = (
            "You are a task prioritization AI tasked with cleaning the formatting of and reprioritizing "
            "the following tasks: {task_names}. "
            "Consider the ultimate objective of your team: {objective}. "
            "Do not remove any tasks. Return the result as a numbered list, like: "
            "#. First task "
            "#. Second task "
            "Start the task list with number {next_task_id}."
        )
        prompt = PromptTemplate(
            template=task_prioritization_template,
            input_variables=["task_names", "next_task_id", "objective"],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)

todo_prompt = PromptTemplate.from_template(
    "You are a planner who is an expert at coming up with a todo list for a given objective. Come up with a todo list for this objective: {objective}"
)
todo_chain = LLMChain(llm=OpenAI(temperature=0), prompt=todo_prompt)

search = SerpAPIWrapper()
tools = [
    Tool(
        name="Search",
        func=search.run,
        description="useful for when you need to answer questions about current events",
    ),
    Tool(
        name="TODO",
        func=todo_chain.run,
        description="useful for when you need to come up with todo lists. Input: an objective to create a todo list for. Output: a todo list for that objective. Please be very clear what the objective is!",
    ),
]

prefix = """You are an AI who performs one task based on the following objective: {objective}. Take into account these previously completed tasks: {context}."""
suffix = """Question: {task}
{agent_scratchpad}"""

prompt = ZeroShotAgent.create_prompt(
    tools,
    prefix=prefix,
    suffix=suffix,
    input_variables=["objective", "task", "context", "agent_scratchpad"],
)

def get_next_task(task_creation_chain: LLMChain, result: Dict, task_description: str, task_list: List[str], objective: str) -> List[Dict]:
    """Get the next task."""
    incomplete_tasks = ", ".join(task_list)
    response = task_creation_chain.run(
        result=result,
        task_description=task_description,
        incomplete_tasks=incomplete_tasks,
        objective=objective,
    )
    new_tasks = response.split("\n")
    return [{"task_name": task_name} for task_name in new_tasks if task_name.strip()]

def prioritize_tasks(task_prioritization_chain: LLMChain, this_task_id: int, task_list: List[Dict], objective: str) -> List[Dict]:
    """Prioritize tasks."""
    task_names = [t["task_name"] for t in task_list]
    next_task_id = int(this_task_id) + 1
    response = task_prioritization_chain.run(
        task_names=task_names, next_task_id=next_task_id, objective=objective
    )
    new_tasks = response.split("\n")
    prioritized_task_list = []
    for task_string in new_tasks:
        if not task_string.strip():
            continue
        task_parts = task_string.strip().split(".", 1)
        if len(task_parts) == 2:
            task_id = task_parts[0].strip()
            task_name = task_parts[1].strip()
            prioritized_task_list.append({"task_id": task_id, "task_name": task_name})
    return prioritized_task_list

def _get_top_tasks(vectorstore, query: str, k: int) -> List[str]:
    """Get the top k tasks based on the query."""
    results = vectorstore.similarity_search_with_score(query, k=k)
    if not results:
        return []
    sorted_results, _ = zip(*sorted(results, key=lambda x: x[1], reverse=True))
    return [str(item.metadata["task"]) for item in sorted_results]

def execute_task(vectorstore, execution_chain: LLMChain, objective: str, task: str, k: int = 5) -> str:
    """Execute a task."""
    context = _get_top_tasks(vectorstore, query=objective, k=k)
    return execution_chain.run(objective=objective, context=context, task=task)

class BabyAGI(Chain, BaseModel):
    """Controller model for the BabyAGI agent."""
    task_list: deque = Field(default_factory=deque)
    task_creation_chain: TaskCreationChain = Field(...)
    task_prioritization_chain: TaskPrioritizationChain = Field(...)
    execution_chain: AgentExecutor = Field(...)
    task_id_counter: int = Field(1)
    vectorstore: VectorStore = Field(init=False)
    max_iterations: Optional[int] = None

    class Config:
        """Configuration for this pydantic object."""
        arbitrary_types_allowed = True

    def add_task(self, task: Dict):
        self.task_list.append(task)

    def update_task_list_display(self, text_edit: QTextEdit):
        text_edit.clear()
        text_edit.append("*****TASK LIST*****")
        for t in self.task_list:
            text_edit.append(f"{t['task_id']}: {t['task_name']}")

    def update_next_task_display(self, text_edit: QTextEdit, task: Dict):
        text_edit.append("\n*****NEXT TASK*****")
        text_edit.append(f"{task['task_id']}: {task['task_name']}")

    def update_task_result_display(self, text_edit: QTextEdit, result: str):
        text_edit.append("\n*****TASK RESULT*****")
        text_edit.append(result)

    def confirm_tasks(self) -> bool:
        return True

    def confirm_task_result(self) -> bool:
        return True

    @property
    def input_keys(self) -> List[str]:
        return ["objective", "text_edit"]

    @property
    def output_keys(self) -> List[str]:
        return []

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent."""
        objective = inputs["objective"]
        text_edit = inputs["text_edit"]
        first_task = inputs.get("first_task", "Make a todo list")
        self.add_task({"task_id": 1, "task_name": first_task})
        num_iters = 0

        while True:
            if self.task_list:
                # Step 1: Pull the first task
                task = self.task_list.popleft()
                self.update_next_task_display(text_edit, task)

                # Step 2: Execute the task
                result = execute_task(
                    self.vectorstore, self.execution_chain, objective, task["task_name"]
                )
                self.update_task_result_display(text_edit, result)

                # Step 3: Store the result in the VectorStore
                result_id = f"result_{task['task_id']}"
                self.vectorstore.add_texts(
                    texts=[result],
                    metadatas=[{"task": task["task_name"]}],
                    ids=[result_id],
                )

                # Step 4: Create new tasks and reprioritize task list
                new_tasks = get_next_task(
                    self.task_creation_chain,
                    result,
                    task["task_name"],
                    [t["task_name"] for t in self.task_list],
                    objective,
                )
                for new_task in new_tasks:
                    self.task_id_counter += 1
                    new_task.update({"task_id": self.task_id_counter})
                    self.add_task(new_task)

                self.task_list = deque(
                    prioritize_tasks(
                        self.task_prioritization_chain,
                        self.task_id_counter,
                        list(self.task_list),
                        objective,
                    )
                )

                self.update_task_list_display(text_edit)

            num_iters += 1
            if self.max_iterations is not None and num_iters == self.max_iterations:
                text_edit.append("\n*****TASK ENDING*****")
                break

        return {}

    @classmethod
    def from_llm(cls, llm: BaseLLM, vectorstore: VectorStore, verbose: bool = False, **kwargs) -> "BabyAGI":
        """Initialize the BabyAGI Controller."""
        task_creation_chain = TaskCreationChain.from_llm(llm, verbose=verbose)
        task_prioritization_chain = TaskPrioritizationChain.from_llm(llm, verbose=verbose)
        llm_chain = LLMChain(llm=llm, prompt=prompt)
        tool_names = [tool.name for tool in tools]
        agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent, tools=tools, verbose=True
        )
        return cls(
            task_creation_chain=task_creation_chain,
            task_prioritization_chain=task_prioritization_chain,
            execution_chain=agent_executor,
            vectorstore=vectorstore,
            **kwargs,
        )

class MainWindow(QMainWindow):
    def __init__(self, baby_agi):
        super().__init__()
        self.baby_agi = baby_agi
        self.initUI()

    def initUI(self):
        self.setWindowTitle('BabyAGI')
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

        self.input_line = QLineEdit()
        self.layout.addWidget(self.input_line)

        self.send_button = QPushButton('Send')
        self.send_button.clicked.connect(self.handle_send)
        self.layout.addWidget(self.send_button)

    def handle_send(self):
        user_input = self.input_line.text()
        self.input_line.clear()
        self.text_edit.append(f"User: {user_input}")

        objective = user_input
        threading.Thread(target=self.run_baby_agi, args=(objective,)).start()

    def run_baby_agi(self, objective):
        self.baby_agi({"objective": objective, "text_edit": self.text_edit})

if __name__ == "__main__":
    app = QApplication(sys.argv)

    llm = OpenAI(api_key="sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t", temperature=0)
    verbose = False
    max_iterations: Optional[int] = 3

    baby_agi = BabyAGI.from_llm(
        llm=llm, vectorstore=vectorstore, verbose=verbose, max_iterations=max_iterations
    )

    main_window = MainWindow(baby_agi)
    main_window.show()

    sys.exit(app.exec_())
