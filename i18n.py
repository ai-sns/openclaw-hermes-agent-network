from globals import global_env
def lt(*args):
    lang=global_env.get("lang",0)
    if len(args)==1:
        txt=args[0].split("|")[lang]
    else:
        txt=args[lang]

    return txt
