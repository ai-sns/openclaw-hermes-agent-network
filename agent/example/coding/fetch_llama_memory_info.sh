# filename: fetch_llama_memory_info.sh
curl -s "https://huggingface.co/docs/transformers/model_doc/llama" | grep -i "405B" -A 10