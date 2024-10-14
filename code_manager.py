# 函数有3中类型：module，file，plugin;
# module是系统内置的各种函数，系统启动时候就加载进去，就像其他普通函数一样可以随时调用，函数在agent.tools中,由于随系统启动，自定义代码容易导致系统出错，所以不提供界面给用户进行添加，用户要添加要通过IDE，修改源码进行添加
# file是以一个独立的python文件存在的，位于pluginsmanager-plugins_function,运行的时候将拷贝到coding中去执行
# plugin一般是提供复杂的功能，有ui，有用户交互，由多个文件组成，比如由python文件，由html文件，有图片等等，位于pluginsmanager下有plugins_gui和plugins_headless，这些插件在系统启动的时候都启动了，所以就像调用内置函数一样调用即可
function_type="module"

#运行模式有两种类型：main_process，subprocess
# main_process:使用eval或者使用exce()函数，可以将结果直接返回当前进程
# sub_process:通过
run_typ="main_process"

def run_function(function_name,function_type,run_type="main_process"):
    out_put=""

    return out_put


def run_code(function_name, function_type="file", run_type="sub_process"):
    out_put = ""

    return out_put
