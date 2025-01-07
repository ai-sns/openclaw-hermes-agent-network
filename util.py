import datetime
import os
import random
import string
import re
import base64
import os


# Format
import subprocess
import sys

import requests


def convert_unicode_to_chinese(unicode_string):
    """
    将字符串中的 Unicode 转换为中文字符

    :param unicode_string: 包含 Unicode 的字符串
    :return: 转换后的中文字符串
    """
    try:
        # 使用 'unicode_escape' 解码字符串
        chinese_string = unicode_string.encode('utf-8').decode('unicode_escape')
        return chinese_string
    except Exception as e:
        # 捕获解码过程中可能发生的异常
        print("解码过程中发生错误:", e)
        return None

def format_string_for_run_javascriptbakbak(t_string):
    # \\`\\`\\`Python
    t_string = t_string.replace("\\\\`\\\\`\\\\`", "\\`\\`\\`")

    # ${
    t_string = t_string.replace("${", "\$\{")

    # \n

    # t_string = replace_newlines_in_strings(t_string)
    t_string = t_string.replace('\\n', '\\\\n')
    #
    # # `\\`
    # t_string = t_string.replace("`\\\\`", "_b_to_traslate_back_slash_slash_")
    #
    # # `\`
    # t_string = t_string.replace("`\\`", "_c_to_traslate_back_slash_")
    #
    # # `
    # t_string = t_string.replace("\\`", "_d_to_traslate_back_slash_backquote_")
    # t_string = t_string.replace("`", "\\`")
    # t_string = t_string.replace("_d_to_traslate_back_slash_backquote_", "\\`")
    #
    # # `\\`
    # t_string = t_string.replace("_b_to_traslate_back_slash_slash_", "\`\\\\\`")
    #
    # # `\`
    # t_string = t_string.replace("_c_to_traslate_back_slash_", "\`\\\\\`")

    # \\`\\`\\`Python
    # t_string = t_string.replace("_a_to_traslate_back_slash_slash_slash_", "\\`\\`\\`")

    t_string = t_string.replace("`", "_cjrok_")

    return t_string


def format_string_for_run_javascript(t_string):
    # \\`\\`\\`Python
    t_string = t_string.replace("\\\\`\\\\`\\\\`", "```")
    t_string = t_string.replace("\\`\\`\\`", "```")

    # ${
    t_string = t_string.replace("${", "\$\{")

    # \n

    # t_string = replace_newlines_in_strings(t_string)
    t_string = t_string.replace('\\', '_sla_cjrok_sh_')

    t_string = t_string.replace("`", "_back_cjrok_slash_")

    return t_string


def format_string_for_run_javascript_user(t_string):
    # return t_string
    # ${
    t_string = t_string.replace("${", "\$\{")

    # \n
    t_string = t_string.replace("\n", "<br>")

    t_string = t_string.replace("`", "\\`")

    # \\
    t_string = t_string.replace("\\", "\\\\")

    return t_string


# 使用正则表达式匹配并替换字符串字面量中的 \n 为 \\n
def replace_newlines_in_strings(s):
    # 匹配单引号或双引号括起来的字符串

    def replace(match):
        string_literal = match.group(0)

        # 只替换字符串字面量中的 \n 为 \\n
        return string_literal.replace('\\n', '\\\\n')

    # 这里的正则表达式匹配包括单引号或双引号括起来的字符串
    return re.sub(r'(\'[^\']*\'|\"[^\"]*\")', replace, s, flags=re.DOTALL)


def add_msg_to_message_window_with_markdown_and_highlight(browser_page, message, line_breaks=1):
    message = format_string_for_run_javascript(message)
    script_string_to_run = 'show_response_msg(`' + message + '`)'
    print("script_string_to_run:")
    print(script_string_to_run)
    browser_page.runJavaScript(script_string_to_run)
    browser_page.runJavaScript('updatemaincontent()')
    line_breaks=0
    line_break = '<br>' * line_breaks
    formatted_message = f'{line_break}'
    browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + formatted_message + '"')

def add_msg_to_message_window_with_markdown_and_highlightv2(browser_page, message, line_breaks=1):
    message = format_string_for_run_javascript(message)
    script_string_to_run = 'show_response_msgv2(`' + message + '`)'
    print("script_string_to_run:")
    print(script_string_to_run)
    browser_page.runJavaScript(script_string_to_run)
    browser_page.runJavaScript('updatemaincontentv2()')



def add_msg_to_message_window(browser_page, message, line_breaks=1):
    browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + message + '`')
    line_breaks = 0
    line_break = '<br>' * line_breaks
    formatted_message = f'{line_break}'
    browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + formatted_message + '"')

def add_msg_to_message_windowv2(browser_page, message, line_breaks=1):
    print("get the message html:",message)

    script_string_to_run = 'show_title_msg(`' + message + '`)'
    print("script_string_to_run:")
    print(script_string_to_run)
    browser_page.runJavaScript(script_string_to_run)

    # browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + message + '`')
    # line_breaks = 0
    # line_break = '<br>' * line_breaks
    # formatted_message = f'{line_break}'
    # browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + formatted_message + '"')

def add_msg_to_message_windowv3(browser_page, message, line_breaks=1):
    print("get the message html:",message)

    script_string_to_run = 'show_user_ask_msg(`' + message + '`)'
    print("script_string_to_run:")
    print(script_string_to_run)
    browser_page.runJavaScript(script_string_to_run)

    # browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + message + '`')
    # line_breaks = 0
    # line_break = '<br>' * line_breaks
    # formatted_message = f'{line_break}'
    # browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + formatted_message + '"')


# def add_attachment_to_message_window(browser_page, directory_path, attachment_list, line_breaks=1):
#     attachment_list = ["c:\\a.doc", "c:\\d.doc", "c:\\c.doc"]
#     file_path = "c:\\a.doc"
#     file_name = "a.doc"
#     attachment_element = f"""<a href="#" onclick="open_attachment('{file_path}')" style="color:red">{file_name}</a>"""
#     browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + attachment_element + '`')
#     line_break = '<br>' * line_breaks
#     formatted_message = f'{line_break}'
#     browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + formatted_message + '"')


def add_attachment_to_message_window(browser_page, directory_path, attachment_list, line_breaks=1):
    # 遍历附件列表
    for file_path in attachment_list:
        # 从文件路径中获取文件名
        file_name = os.path.basename(file_path)

        # 使用directory_path和file_name重新形成新的file_path
        new_file_path = os.path.join(directory_path, file_name)

        # 根据文件扩展名判断是否为图片
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        file_extension = os.path.splitext(new_file_path)[1].lower()

        # 转义反斜杠
        image_file_path = os.path.abspath(new_file_path).replace("\\", "/")
        new_file_path = new_file_path.replace("\\", "\\\\\\\\")


        if file_extension in image_extensions:
            # 如果是图片，创建 img 标签
            attachment_element = f"""<br><br><a href="#" onclick="open_attachment('{new_file_path}');return false;" style="color:blue"><img src="file:///{image_file_path}" alt="{file_name}" style="width:300px;height:auto;" /></a><br><br>"""
        else:
            # 否则，创建 a 标签
            attachment_element = f"""<a href="#" onclick="open_attachment('{new_file_path}');return false;" style="color:blue">{file_name}</a>&nbsp;&nbsp;&nbsp;&nbsp;"""

        print(attachment_element)
        # 添加附件元素到页面中
        browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += `' + attachment_element + '`')

    # 处理换行
    line_break = '<br>' * line_breaks
    formatted_message = f'{line_break}'

    # 添加换行到页面
    browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + formatted_message + '"')


def get_myai_send_msg_title_formatted(page_index, createtime=None,show_checkbox="none",checked="",record_id=""):
    if createtime is None:
        createtime = datetime.datetime.now()
    if record_id:
        div_id = f"id_{record_id}_a"
    else:
        div_id = f"msg_div_{page_index}"
    message = f"""
    <div style="display: flex; align-items: center;" id="{div_id}" data-value="{page_index}v" data-text="{page_index}t" data-index="{page_index}i" onmouseover='handleMouseOver(this)' onmouseleave='handleMouseLeave(event)'>
		 <input class="styled-checkbox" style="display:{show_checkbox}" {checked} type="checkbox" id="msg_checkbox_{page_index}" data-id="{div_id}" data-value="{page_index}" onclick="add_to_selected_msg(this,'question')">
		 <img src="file:///images/ybot.png" style="width:18px;height:31px">
		 <span style='color: darkred;font-size:18px;margin-left:5px'>我的AI</span>
		 <span style='color: #c0c0c0; font-size:18px;;margin-left:10px'>{createtime.strftime("%Y-%m-%d %H:%M:%S")}</span>
    </div>
        """

    return (message)

def get_user_ask_msg_title_formatted(page_index, createtime=None,show_checkbox="none",checked="",record_id=""):
    if createtime is None:
        createtime = datetime.datetime.now()
    # message = f"""<strong><em><span style='color: darkred;font-size:14px;'>用户: </span><span style='color: #c0c0c0; font-size:14px;'>{createtime.strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><input type=checkbox><input type=button onclick='alert(1)'>"""
    if record_id:
        div_id = f"id_{record_id}_a"
    else:
        div_id = f"msg_div_{page_index}"
    message = f"""
    <div style="display: flex; align-items: center;" id="{div_id}" data-value="{page_index}v" data-text="{page_index}t" data-index="{page_index}i" onmouseover='handleMouseOver(this)' onmouseleave='handleMouseLeave(event)'>
		 <input class="styled-checkbox" style="display:{show_checkbox}" {checked} type="checkbox" id="msg_checkbox_{page_index}" data-id="{div_id}" data-value="{page_index}" onclick="add_to_selected_msg(this,'question')">
		 <img src="file:///images/user.png" style="width:18px;height:25px;">
		 <span style='color: darkred;font-size:18px;margin-left:5px'>用户</span>
		 <span style='color: #c0c0c0; font-size:18px;;margin-left:10px'>{createtime.strftime("%Y-%m-%d %H:%M:%S")}</span>
    </div>
        """

    return (message)


def get_user_ask_msg_content_formatted(content):
    # message = format_string_for_run_javascript_user(content)
    message = format_string_for_run_javascript(content)
    # message = f"""<div style='margin-left:24px'><p>{message}</p></div>"""

    return (message)


def get_agent_reply_msg_title_formatted(model_name, page_index, createtime=None, show_loading=True,show_checkbox="none",checked="",record_id=""):
    loading_img = "data:image/gif;base64,R0lGODlhDAAMAPcAAGi77nPA8H3E8X3F8YHG8YnK8orL8ozL8pDN85LO85fQ9JjR9JrS9J7T9KHV9aXW9anY9avZ9q3a9rDb97Hc9rLc97Pc97Pd97Td97nf97vg97zh+L7i+MDj+MHj+MPk+MTl+MTl+cXl+cfm+cjm+cnn+crn+cvn+czo+czo+tDq+tHq+tLr+tPs+dTs+tXs+tXs+9bt+9jt+9ju+9nu+9ru+9zv+97w/N/x++Dw/ODx/OLy/OTz/Of0/Oj1/On1/er1/Or2/ev2/ez2/ez3/e33/e73/e74/e/4/fD4/fH5/fL5/fL6/fP5/fT6/vX7/vb8/vf7//f8/vj8/vz9/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////yH/C05FVFNDQVBFMi4wAwEAAAAh+QQJAwBVACwAAAAADAAMAAAIkwCrVFlRoYoUKVWWIBRYRQSBGAenBHki8IUJJA4eMIGSJAkVJU4yHIBAYcCHI0CK+NBBpEoNCQUEJGiBA8cPihYsTEAAQCAIGDl06Mg5QUEAgRdS3BBaRceGBgwMLNBQooaRhg4yhIAgAQOHGTJO4LDhoomHDyNIsFARpccQgTQi8DBhQkiHHQyboqhCtwoNHwIDAgAh+QQJBABTACwAAAAADAAMAIdsve54wvCAxvGCx/GFyPKNzPKPzPOQzfOUz/OX0PSa0vSe0/Se1PWi1fWl1vWo2PWs2vat2vav2/aw2/ay3Pez3Pez3fe03fe13ve23ve53/e53/i74fe84fi/4vjD5PjE5PjE5PnG5fnH5fnH5vnI5vnK5/nL5/rL6PrM6PnN6PrO6fnP6frS6/rT6/rV7PrW7PrW7frY7fvZ7vva7vvb7vvb7/vd7/ve8Pvi8vzj8vzj8/zk8/zl8/zp9f3r9v3s9v3t9/3u9/3u+P3v+P3w+P3z+f7z+v70+v30+v71+v72+/73/P74/P/5/P76/f76/f/7/f/8/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IlACnTGmBYUqUKFOUOBEokAQBGQefDGEiMEaKIg4eLIFyxIgUI0o4HIBwYUCJJEKK/OAhZIqNCQUEJKChQweQJVMyZLCAAIBAEzN28OChs4KCAAI3tMgxdEoODw0WGGDgYcUNIlNKOOgwIgIFDR9q2GCRAwcMJCBEnEDxwkUTH0EE1pDQQ4UKICF4MHTKYopdlz4EBgQAIfkECQMARgAsAAAAAAwADACHPafqTK7rT7DrXbbtcb/vfMTwg8fyjMvyls/zodX1o9X0pdb1ptb2qNf1rdr2rtv2s933tNz2t9/3vOD3vOH4veH3vuL4w+P4w+T4xeX5xuX5y+j6zun6z+n60uv61Ov61ev61ez71uz61uz72Oz62O362u772+763e/73vD74fH84vL85PP86fT86fX86fX96vX86/X86/b86/b97Pb97ff97vf97/f+8Pj+8fj99Pr99Pr+9fr+9vv+9/v++Pv++fz++v3/+/3//P3+/f3//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAjRhR4cFIkSJGhAwRKBBHAIMIayA0wiKHEQQLDvbQYWRIEBEDEhgBcIOIDCMzUPgQ+ECAAgxAbJiwIZBDhw4XGghsEcOGTw5AM0QQeOKFT5pGLBCosCHEBwkpBKYoAMGIARAkGBgpMcGGix1GKGhIkWJEByNBwBrhccAIWSMOfjA0QmOF26gwLBoJCAAh+QQJAwBJACwAAAAADAAMAIdFq+tTsexWs+1juO55w/GDx/GKyvKTzvOa0fSk1fSn1vWp2Pas2PWs2fas2vax3Pez3fe03Pa33va33/e+4fe/4ffA4vjA4/jB4/jD5PjG5fnI5vnJ5vnO6frQ6vrR6vrS6vrU7PvY7frY7fvY7fzZ7vva7vvb7vrc7/vf8Pvg8fvg8fzh8fvi8vzj8vzk8/zl8/zq9fzs9vzs9v3t9/3v+P7w+P3x+P3x+f7y+f3y+f7z+f71+v71+/72+/74+/74/P75/P75/P/6/P77/f/8/f79/v79/v/+/v7///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiwCTJGkRIokFC0mKGBEo0EYAgwh3IBEIQ0cSBAsOBvmR5AiREQMSJAEQoYLFGi6ACHwgQAGDEzlU3BDo4cMHDQ4EyqiBo6eHnxskCEwxoycOgRgIXOhAYgQFFgJXFJiQxIAIEw2SoMhgI0YPgxxUqCgBIskQHgJ9HEgiNgkEIQyT0HjBVkWSGTkEBgQAIfkECQQASAAsAAAAAAwADACHS63rWbTtXbXtabvuf8XxicnykM3ymdH0ntP0qNf1qdf1rNn2r9r2sNv3tN33t973ud/3ut/3vOD4wuP4w+P3w+T4xOT5xeX5yOb4yeb5yef5zOj50Or60ur60+v61ez61uz62e362+372+783O783O/73e/73vD64PH84fH74/L85PP85fP85vT86PX96vb96/b97vf97/j+8Pj98fn+8vn98vn+8vr+8/r+9Pr+9fr+9fv+9vr+9vv99vv++fz++v3++/3//P3+/P3//P7//v7+/v7//v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAkSBR8QHJhAlIjBQRKJBGAIMIfzBsUQMJggUHhQxBcoRIiAEJkAB4MEEijhdABDoQoIDBiR4udgjs4MEDhgYCZ9zAwbODzwwSBKqQwROHQAsEKHAYQeLCCoEpCkRAYkCECQdIUGiwAUMHkgobVKgoAQJJEB8CeRwYqAIJBIkMY7BgiyRGDoEBAQAh+QQJAwBCACwAAAAADAAMAIdSsOxgt+5kue5wv/CHyfKQzfOY0fSg1PWi1fWs2fat2vav2vay3Paz3Pa33ve53va64Pi+4fi/4fi/4vjE5PjG5PjH5fjH5fnL5vnM5/nM6PnP6fnQ6vrT6vrU6/rV7PrX7fva7vvb7/vd7/ve7/zf7/vf8Pvg8fzh8fvj8vzk8vzk8/zl8/zn9Pzo9f3s9v3u9/3v9/3v+P3w+f7x+P3z+f3z+f70+f71+v71+/72+/73+/74/P/6/f76/f/7/f79/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IgwCFCFEBQggFCgITCqQRwCBChS1sCEGw4GDCIEBEDEggBMCDhzpm/BDoQIACBih6wOAh0MOHDxgaCLxxA4dNDzgzSBDYgoZNHAIvEKjQgUQJDS4EpigQQYiBEScgCFnBocYLHUIsbGDBwkQIIT92CNxxQAhXIRN8KJTRwiwLITFyCAwIACH5BAkDAEkALAAAAAAMAAwAhzel6Uar61m07Wa672u873bB8I3L85PO85bQ9J7T9KLV9KXW9abX9avY9bDb9rDc97Lc9rTc9rbe97ne9rvg97vg+L7h98Hj+MLj+MLj+cbl+Mbl+crm+Mrn+cvn+czn+M/p+tDp+dLq+tPr+9br+tbs+tft+tft+9jt+t3w/N7w/ODw/ODx/OLx++Lx/OPy/OXz/Of0/Oj0/On1/er1/Ov2/e32/e/3/fD4/fH5/vL5/vP5/fT5/vX6/vb7/vf7/vj7/vj8/vj8//r8/vr9/vv9//z9//3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkgYEiiQYNSUKwEChQxwCDCAPcEChjR5IFEA4qOCAQSYoCDpIIoDABQBIiPo4IrEDgQYQGFnwUEXjChIkPEgQG+cHzx4mfIDAIpMGjp8AOBjiQWOFiRA2BMBBkSJKARYsLSWKU6GHDRxIPImLEeKEiiREgAoUwyBojyYYhDJPgmME2SQ6vSQICACH5BAkEAEIALAAAAAAMAAwAhz2n6kyu62C37my873G/73zE8JXP9JbP853T9aXW9abW9qnY9a3a9q7b9bPd9rbe97jf97nf973h+L7i+L/j+MLj+Mbk+cbl+cjm+cnn+czn+c3o+c7p+s/p+tLq+tLr+tbs+9nu+9ru+93v+97w++Hx++Hx/OLx/OPy/OXz/ebz/Ob0/en1/On1/er1/Ov2/e72/O73/e/4/vD4/vH4/fL5/fP6/vT6/vb6/ff7/vj7/vn8/vr9//v8/vv9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIUIUSFCSIYMQj6YECjQxgCDCAPMEMjihpAFDw4mOMCQRAEHQgRQkABASBAgDCcQcAChQQUgQQSGmNkhgsAeO3LumBnCgwWBMHDoFMjBwAYRKAjGEKgCwQUhCk6kwCDkxYgcMnII6QCiRYsVJYT84CFQBwMhXoVo8MFQCA0XaFsIqaFVSEAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zlM3ymtH0m9LzodT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t973ueD3uuD3vOD3v+H3weL4weP4yef5y+f5z+n60Or60er60ev60ur60+v61Ov61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j97/j+8Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAnTiRkcJJhw5OSrgQKHBIAYMIB/gQeKOIEwgWDjpQ4ITHihYHKjghoCGDACcIAnwQuMEAhQsSEgBgIBDFiRMiMAiMkEOJTxRASXAQCASJTyUCQSwIoWIGDhZBBNJoMPRBjBoenPR4ceSHESciTOjQYQOGkyZLBCaZ4GSskxFMGDoRsqOtDidEjggMCAAh+QQJAwBJACwAAAAADAAMAIc6pulJretLretZtO1uvu55wvB/xfGJyfKVz/OXz/Oe0/Si1fSk1vWq2fas2fax3Pay3Paz3Pa03fe53va53/e74Pi84fe94ffA4vjB4/jE5PjE5PnM5/jN6PnR6vrU6vrU6/rU6/vV7PrW7PrX7frZ7vrc7/vd7/vd8Pvf8Pzg8fvh8fvj8vzn9Pzo9f3p9fzp9f3q9fzq9v3r9v3s9v3t9vzt9/3u9/3u+P3v9/3x+f7z+v70+v71+v31+v71+/72+/74/P75/P76/f78/f78/v78/v/9/v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IjACTJIFxIkmHDklEsBAokEcBgwgH6BA4w0eSBxYOOlCQJIeKFQcqJCGgIYOAJAgCeBC4wcCECxESAGAgEMWJEx8wCIRQ44hPFEBJcBDYo4jPIwJBLAiRQgYOFz8EymiAUEKLGCOS7JAxREeQJCNM2LBB40USJEYECqGQZGySEkQYJuFxo62NJECECAwIACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9JvR86LV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg97/i+MDi98Pj+MTk+Mbk+cfl+c/p+tDq+dHq+tPr+tfs+tft+9jt+9ns+tru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIsUWUGiiAYNRT6oECgwRwGDCAfcEOhiR5EHFA42UFCExokUBygUIYDBgoAiCAJ0EJjBwIQKERIAWCCQhAkTIC4IhECDIYmfITYI/EGEoUAPDDygeHEjhg+BLBxwKCKhhYwRRXbYEIKjRxERJGqIhVGEyBCBQUSKLVLiLEMdM4qs5QFEYEAAIfkECQMAQQAsAAAAAAwADACHSK3rVrPsWbTtZrrvfMPwhsjxjcvzltD0nNL0ntP0odT1pdb1qtj1sNv2stz2tt32t973uN73ud/3weP4wuP4w+P4xuX4xuX5yOX5yuf50er60+r61Ov61ez62O362u772+762+772+/73fD83vD84fH74fH84vH74vL84/L85PP85fL85fP85vT86/b97fb97ff98Pf98Pj98fn+8vn+8/n+8/r+9fr+9vv++fz++vz++v3++/3++/3//f7+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAgwRxYSKIBg1BPLAQKPBGAYMIB9AQ+AJHkAgUDjpYEGTGCRYHKAQhgOGCgCAIAnAQmMHAhAoSEgBgILAEChQfLAhUAIGCzxJAQWwQOGKC0QkCRTQIsSLGDRw9BMJ40CHIhBcyVATZgeNHjRxBSKSgQcOGDIFABOq4EIRskBY+GAbBMaPtxBw8BAYEACH5BAkDAEIALAAAAAAMAAwAh0+w61227WC37my874PH8ozL8pXP9J3T9aDU9KLV9aXV9anY9a7b9rbe97ff97ne97zg97zh97zh+MPj+MPk+MTk+cbl+Mbl+cjm+cnm+crm+czn+c7p+tPr+tbr+dbs+tjt+tru+9zv+97v+97w+9/x/ODw/OHx++Ly/OTz/Obz/Ob0/en1/ev2/Oz2/e33/e73/e/4/vD4/vH4/fL5/fP5/vP6/vT6/fT6/vX6/vb7/vf7/vn8/vr9//v9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIUIcYFCSIcOQkKoECgwRwGDCAfYEBhjhxAJFw42WCBkRgoVBy4IIaAhgwAhCAJ8EMjBwAQLERIAYCAwhU0RGgQqeFChp80UJTwINEGhKAWBJByMYIGDB5AgAmFAACEEg4waLYQEASIERw8hJ1bgwKHjBkOBPjZ0xSHkBVSGO2isFeLjh8CAACH5BAkEAEwALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pHN85PO85vS85zS9KLV9aPW9aTW9aXW9ajY9a3a9rHc97je9rng97zg+L7h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+crn+cvn+szo+c7p+c7p+s/p+tDq+tHq+tPr+tbt+9jt+9rt+tzv+97w+9/w++Hx++Hx/OLy/OTz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiNAJkwuQGDyYkTTFTQEChQCAKDCAv0ELhjCJMLHQ5OgMCER4waDDwwMSDiAwEmDQagEFgiwQYOFhwIiCBwhgwZK0IIfEBBg88ZQF2kEKhAQoajAltUeIFjCAgACwTqwKCCyQgfQHgwORCARJAjTGLYECLECBEmOVgITGKCCVkmPZYwZFLkh1shTJAoERgQACH5BAkDAEsALAAAAAAMAAwAhzqm6Umt61217Wm77m6+7nnC8JDN8pXP85nR9J/U9aLV9KXW9ajX9ajY9qrZ9qvZ9rHc9rTd97re97zh977h98Hi+MPk+MXl+cfl+cjm+cnn+cro+cvo+czo+c7o+s7p+s/p+dDo+tHp+dHq+tTr+tbs+tjt+9nt+tnu+t3v+97w/ODx++Dx/OHx++Ty/eTz/OXz/Ob0/Ob0/ej0/Oj0/en1/On1/er2/ez2/e73/e/3/fD5/vH5/vL5/fL5/vT6/vX6/fb6/vb7/vj8/vn8/vr9/vv9//z9/vz9//7+/v7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJcsyQFjiQkTS1LYECgwCAKDCAv8EMhjyBILHQ5OgLCkR4wbDj4sMRDCA4ElDQacEEhCwQYOFRgIiCCQxowZLUQIfEAhg08aQF2oEJhAAoajAl9ckLGjCAgACwT60MBiSQkgQ4gsORBghBAjS2rgGDLkCJIlOlYIPIJiCdklWhnCFeLWopIkAgMCACH5BAkDAEsALAAAAAAMAAwAhy+h6D+o6kGp6VCw7GS57nC/8HXA8H/F8I/M85jR9JnR9J7T9J/U9aDU9aLU9ajY9anY9avZ9qzY9q7Z9bDb9rTd9rfe973h+L7h97/i+MDi+MTj+Mfl+Mrn+czo+c3o+M7o+c/p+c/p+tDp+tDq+tHq+tPq+tPr+tXs+tfs+tru+9vv+93v+9/w+9/x/ODx++Hx++Lz/OPx/OTz/Obz/Of0/Oj1/en0/Or1/er2/ev2/O33/e/4/e/4/vD4/fD4/vL5/vP5/fP5/vT6/vf7/vj7/vj8/vr8/vr9/vv9/v3+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJcs4VFjiQoVS1rgECiQSAODCA8MEQikyBIOIQ5mqLBESA0dFEosSWBihIElEQqsEJgCwgcQGyQQsCAQh00ZKARO0NChp00cNGIIdIChZweBNjzcEHJhgYAHAoOQmLGEhZEcAJYoGHCCSJIlO34gQcIAwRIfMAQqebFk7JIAPRguOUKkLZIlIlwIDAgAIfkECQQATAAsAAAAAAwADACHN6XpRqvrSK3rVrPsa7zvdsHwfMPwhsjxk87znNL0ntP0oNT0otX0pdb1ptf1q9n2r9v2sNv2sdv2tt32uN73u+D4wOL4wOP5wuP3wuP4x+X5y+f5zOj5zOj60On50en50er50ur60+r60+v71Ov61ez61ez71uz62e372+/73O/73fD84PH84fH84vH75PP85fP85vP85vT85/T86PT86fT96fX96/b97PX87Pb97fb97ff97/f98Pj98fn+8/n98/n+8/r+9fr+9vr++Pv++Pz/+fz++vz9+/3+/P3+/P3//f7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAmTDpYYOJChVMWtwQKLCIA4MIDwgRCMQIkw0hDmagwOQHjR0TSjBRYEKEASYQCqwQmCICiA8aIhCoIDCHzRgoBErAwKGnzRw1YAhscKGDUYE3RugYYmGBgAcChZyYweTFERwAmCQYQIKIkoFBkiRhgICJDxcCl8hgIpZJAB4MmSCx2NYDC4EBAQAh+QQJAwBFACwAAAAADAAMAIc9p+pMrutPsOtdtu1xv+98xPCDx/KMy/KWz/Og1PSj1fSl1vWm1vao1/Wt2vau2vaz3faz3fe03Pa33/e84Pe84fi+4vjC4/jD5PjG5fnL6PrO6frP6frS6/rU6/rV6/rV7PvW7PrW7PvX7PrZ7vva7vvb7vrd7/ve8Pvh8fzi8vzk8/zp9Pzp9fzp9f3q9fzr9fzr9vzr9v3s9v3t9/3u9/3v9/7w+P7x+P30+v30+v71+v72+/73+/74+/75/P76/f/7/f/8/f79/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiQCLFMHxoggKFEVUzBAo0IcDgwgP7BCoA0gRDiIOZqhQREeLGhRIFGEw4oOBIhEKIDQ4wQMIDRAIWBBYo6YLEwIlZODAs2YNGCwENriwoSjNEjh+YFAg4IHAHidkFIkxxAaAIgkGhAAipEgOHkSILEAwcIVAIjSKhC0S4AbDIkKCqCVSpEMKgQEBACH5BAkDAEkALAAAAAAMAAwAh0Wr61Ox7Faz7WO47nnD8YPH8YrK8pPO85rR9KTW9afW9anY9qzY9azZ9qza9rHb9rPd97Tc9rfe9rff977h97/h98Di+MHj+MPk+MXl+cjm+cnm+c7p+tDq+tHq+tLq+tTs+9jt+tjt+9jt/Nnu+9ru+9vu+tzv+9/w++Dx++Dx/OHx++Ly/OPy/OTz/OXz/Or1/Oz2/Oz2/e33/e/4/vD4/fH4/fH5/vL5/fL5/vP5/vT6/fX6/vX7/vb7/vj7/vj8/vn8/vn8//r8/vv9//z9/v3+/v3+//7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkwSEjSYoUSVzMEChQCASDCA/4EMhjSJIPJA5usJCkB4waGE4kaVAihIEkEwqoELiCgogRHCYQuCDwhk0ZKARK0OChp80bNGIIdJChg1GBNlLsMMFAgYAHAoG0oJEkR4UIAJIkGCCCyJEkP4JYsLAAQdUXApHoSDI2SYAaDJMYKcKWIwgWAgMCACH5BAkEAEkALAAAAAAMAAwAh0ut61m07V217Wm77n/F8YnJ8pDN8pnR9J7T9KjY9qnX9azZ9q7a9bDb97Td97Xd97fe97nf97rf97vg97zg+MLj+MPk+MTk+cXl+cfl+Mnn+crn+czo+dDq+tLq+tPr+tXs+tbs+tnt+tvt+9vu/Nzu/Nzv+93v+97w+uDx/OHx++Py/OTz/OXz/Ob0/Oj1/er2/ev2/e73/e/4/vD4/fH5/vL5/fL5/vL6/vP6/vT6/vX6/vX7/vb6/vb7/vj8/fn8/vr9/vv9//z9/vz9//z+//7+/v7+//7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiJAJMk0SEjyYoVSVoUFJgESASDCA/0EOhDSJIQJg5ysJBkR4wbGlIkcXBihIEkEgqoEMgCQwkSHSYQuCAwh80ZCJNQ2PChp80cOGgIbJDBg1GBPF78QMFAgYAHAoPAyNGwAgQASRIMEFEESRIiQypUWIAgiQ0XDIEkEZskQA2GSYwcWVshCYicAQEAIfkECQMAQQAsAAAAAAwADACHUrDsYLfuZLnucL/wh8nykM3zmNH0oNT1otX1q9n2rdr2r9r2stv1s9z2uN/3ud72uuD4vuH3vuH4v+H4v+L4xOT4x+X4x+X5yuX5zOj5zej5z+n50Or60+r61Ov61ez61+372u772+/73e/73u/83+/73/D74PH84fH74/L85PL85PP85fP85/T86PX97Pb97vf97/f97/j98Pn+8fj98/n98/n+9Pn+9fr+9fv+9vv+9/v++Pz/+v3/+/3+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIMAgwTJESMICxZBWsgQKLAHBYMID+wQuMNHkBAmDm6wEETHixocVgSBcGKEgSASCqQQ6CJDCRIdIhC4IBCHTRotBE7Q8KGnTRw3bghsgMGDUYE8YPhAwUCBAAcCfczQIbDCAwBBEgwQ8QMIwwoVFiAIYiMnwyBggwSgcfZrhSAgVAgMCAAh+QQJAwBJACwAAAAADAAMAIc3pelGq+tZtO1muu9rvO92wfCNy/OTzvOW0PSe0/Si1fSl1vWm1/Wr2PWv2/aw3Pey3Pa03Pa23ve53va74Pe84Pe/4vjB4/jC4/fC4/jC4/nG5fjG5fnK5/nL5/nM5/nP6fnQ6fnS6vrT6/vW6/rW7PrX7frX7fvY7frd8Pze8Pzg8Pzg8fzi8fvi8fzj8vzl8/zn9Pzo9Pzp9f3q9fzr9v3t9v3v9/3w+P3x+f7y+f7z+f30+f71+v72+/73+/74+/74/P74/P/6/P76/f77/f/8/f/9/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhwCTJPGRI0mMGElm4BAocAgHgwgZCBEIxEgSFS8OivAw0EaPEggvtGCRIIkGBDAE1hjhYgUJDAY6CPxBkwcNgRlAmNhJk2YQgRI+nBgqsIgPCw0iPCBAQeARH0SSAJhQQUASBwVSIBF4QMGGDRAWJNkhQ+CNAEm+Jhmgg2ESFiHSbkiCImWSgAAh+QQJBABDACwAAAAADAAMAIc9p+pMrutgt+5svO9xv+98xPCVz/SWz/Od0/Wl1vWm1vap2PWt2vau2/Wz3faz3fe23ve43/e53/e94fi+4vi/4/jD5PjG5PnG5fjG5fnI5vnJ5/nM5/nO6frP6frS6vrS6/rW7PvZ7vva7vvd7/ve8Pvh8fvh8fzi8fzj8vzl8/3m8/zm9P3p9fzp9f3q9fzr9fzu9vzu9/3v+P7w+P7x+P3y+f3z+v70+v72+v33+/74+/75/P76/f/7/P77/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhQCHDNFhY4gLF0Ne1BAo8AcHgwgZ7BDYA8gQEywOhvAwcIYOEjCGaFCBQsGQDAhWCJQxYkWKERgMdBDIo2aOGAIvfBDBs2ZNHwIleOApQqCQIBYaRHBAgALDIEKGAJhQQcCQBwVKMDyQYMMGCAuG4GghkEaAIV6HDLjBcMgJEGg3DGkpMCAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zmtH0m9LzoNT0odT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t9/3ueD3uuD3vOD3v+H3weL4wuT5yef5yuf5y+f5z+n60Or60er60ur60uv60+v61Or61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j98Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAnTg5QsTJjh1OeAgRKJAJCYMIJyQRuKSJkxg3Dp4Q4cTIjyMwejj5YEPGAyccGtQQGKRFDhorOigIIVCJTSRABHIogaKnTSU6IgjEMCKFUYEMACyQcIGCgQ0CQQRA4ERABg0EnFQ44IKFyAQOPHiwAMFJERwCfQxwItZJgSEMnbwwwdaDExUzBAYEACH5BAkDAEgALAAAAAAMAAwAhzqm6Umt60ut61m07W6+7nnC8H/F8YnJ8pXP857T9KLV9KPU9aTW9arZ9qzZ9rHc9rLc9rPc9rTd97ne9rnf97rf97zh973h98Di+MHj+MTk+MXl+czn+M3o+c7o+tHq+tTr+tXs+tbs+tfs+tnu+tzv+93v+93w+9/w/ODx++Hx++Py/Of0/Oj1/en1/On1/er1/Or2/ev2/ez2/e32/O33/e73/e74/e/3/fH5/vP6/vT6/vX6/fX6/vX7/vb7/vj8/vn8/vr9/vz9/vz+/vz+//3+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJEgCfIDSY0aSGzsEChwCAmDCCkEEVjkCBIXMw6WEIEESA4hMXQgEQGDhQQkHRrEEOijxY0YKDwoACHQiE0iPARyGGGip00jNCAIxADihFGBDAAsiHBhgoENAj8EQIBEQAYNBJBUOKAiBQ4kCRx06GDhAZIeMgTmGICyA5ICCxmuCNEWiYkXAgMCACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9KLV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg977h+L/i+MDh98Pj+MTk+Mbl+cjm+c/p+tDq+dHq+tLq+tPr+tfs+tft+9nt+9ru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIsUAcKjSI0aRWboEChwSAmDCCkEaUikCIyDNUiIKNIDhxAbO4qMkNEiQhEODVgI9BHjxgsUHRZ8YCiQyA+BG0KY2MmQxgOBFz6QGCpQAQAFECpIMJBBoIcACIoIsICBQJEJB1KcoFEkAQMNGig4KLLDhcAbA4qALVIgB00VINRqKEJihcCAACH5BAkDAEIALAAAAAAMAAwAh0it61az7Fm07Wa673zD8IbI8Y3L85bQ9JzS9KHU9aXW9anY9qrY9bDb9rLc9rbd9rbe97je97nf98Hj+MLj+MLj+cPj+Mbl+Mbl+cjm+cvn+dHq+tPq+tTr+tXr+tXs+tjt+tnt+tvv+9zv+93w/N7w/OHx++Hx/OLx++Ly/OPy/OTz/OXy/OXz/Ob0/Ov2/e32/e33/fD3/fD4/fH5/vL5/vP5/vP6/vX6/vb7/vn8/vr8/vr9/vv9/vv9//3+/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiLAIUI6aFDSI0aQmjkECjwhwuDCDHsEBhE4IwbB1WUEKLDBpAcPISsmAFjgpAPD2II9JEDhwwWHhqIEDiBgk0SAjmMSMFzgk8ICQReCGGiqEAGABZIsDDBgAaBHQIgECIAQwYCQiocaIGChhAFDjZsoBBBSA4YAmsMECJWSAEcDIW0AMF2g5ATLwQGBAAh+QQJAwBDACwAAAAADAAMAIdPsOtdtu1gt+5svO+Dx/KMy/KVz/Sd0/Wg1PSl1fWp2PWt2fWu2/a23ve33/e43va84Pe84fe84fjD4/jD5PjE5PnG5fjG5fnI5vnJ5vnK5vnK5/nM5/nO6fnT6/rW6/nW7PrY7frZ7fva7vvc7/ve8Pvf8fzg8Pzh8fvi8vzk8/zm8/zm9P3p9f3r9vzs9v3t9/3u9/3v+P7w+P7x+P3y+f3z+f7z+v70+v30+v71+v72+/73+/75/P76/f/7/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhgCHDAHyY0iOHENq8BAoUAgMgwg5FGQ4BMeOgyxQDPGBMIiQIS5szMAwJASEGA2D9MjRQoSDEgIpVJh5QuAHEypyUtj5IIFADSRyqhDIAMCCCBYmGOggEEQABEMEZNhAYMiFAytU0BiioIEHDxckDOEhQ+CNAUO+Dimgg+KKEWk9DEnxQmBAACH5BAkEAEoALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pLN85PO85vS85zS9KHU9aPW9aTW9ajY9a3a9rDb9rHc97nf97ng97vf977h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+cnn+cvn+szo+c7p+c7p+s/p+tDq+tHq+dPr+tbt+9jt+9rt+tzv+97w/N/w++Hx++Tz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJUoQWJECRAgSnoMESgwyQ6DCE0cEcjihhIhRA7SeKGkyA8SAQ4o0eGDxwglKjDgELgAAIggNlZUaCEwgwYNEhQITNEChs8MQCk4EBhiRYyjAiMIgGCBw4YEJQSiGNBACYEPIgwo8cBgxgsdSh5MOHGiwwUlQXII3FFACVklCBAylKHC7QklLmoIDAgAIfkECQMASwAsAAAAAAwADACHOqbpSa3rXbXtabvubr7uecLwkM3yltD0mdH0n9T1otX0pNb1qNj2qtn2q9n2sdz2stv1tN33u9/3vOH3veD3weL4w+T4xeX5x+X5yOb5yef5yuj5y+j5zOj5zej5zuj6z+n50Oj60en50er61ez61uz62O372e362e763e/73vD84PH74PH84fH84fL85PL85PP85fP85vT86PT86PT96fX86fX96vb97Pb97vf97/f98Pn+8fn+8vn98vn+9Pr+9fr99vr+9vv++Pz++fz++v3++/3//P3+/P3//v7+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAlyxJomTJkCFLhBARyHDhwSUojghcoWMJkiMHcdRYYkTIiAAHlhAZAqTEEhYafAhcAABEkR0uLsAQiCFDBgkJBKp4MaMnhp8UHAgU0YKGUYERBECowGGDAhICTwxgsITAhxAGlnhocENGjyUPJpgw0cGCQR4CfxRYMnYJgiAMl9hIwdbEkhg5BAYEADsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="

    if createtime is None:
        createtime = datetime.datetime.now()
    if show_loading == False:
        display_setting = "display:none;"
    else:
        display_setting = ""

    if record_id:
        div_id = f"id_{record_id}_r"
    else:
        div_id = f"msg_div_{page_index}"
    message = f"""
    <div style='display: flex; align-items: center;' id="{div_id}" data-value="{page_index}v" data-text="{page_index}t" data-index="{page_index}i"  onmouseover='handleMouseOver(this)' onmouseleave='handleMouseLeave(event)'>
         <input class="styled-checkbox"  style="display:{show_checkbox}" {checked} type="checkbox" id="msg_checkbox_{page_index}" data-id="{div_id}" data-value="{page_index}" onclick="add_to_selected_msg(this,'answer')">
         <img src="file:///images/ybot.png" style="width:18px;height:31px">
         <span style='color: darkblue; font-size:18px;margin-left:5px'>{model_name}</span>
         <span style='color: #c0c0c0; font-size:18px;margin-left:10px'>{createtime.strftime("%Y-%m-%d %H:%M:%S")}</span>
         <img class='imgcls' style='width: 15px; height: 15px;margin-bottom:7px;margin-left:20px;{display_setting}' src='{loading_img}'>
    </div>"""
    return (message)

def get_aifriend_msg_title_formatted(page_index,friend_name, createtime=None, show_checkbox="none",checked="",record_id=""):

    if createtime is None:
        createtime = datetime.datetime.now()

    if record_id:
        div_id = f"id_{record_id}_r"
    else:
        div_id = f"msg_div_{page_index}"
    message = f"""
    <div style='display: flex; align-items: center;' id="{div_id}" data-value="{page_index}v" data-text="{page_index}t" data-index="{page_index}i"  onmouseover='handleMouseOver(this)' onmouseleave='handleMouseLeave(event)'>
         <input class="styled-checkbox"  style="display:{show_checkbox}" {checked} type="checkbox" id="msg_checkbox_{page_index}" data-id="{div_id}" data-value="{page_index}" onclick="add_to_selected_msg(this,'answer')">
         <img src="file:///images/robot.png" style="width:18px;height:24px">
         <span style='color: darkblue; font-size:18px;margin-left:5px'>{friend_name}</span>
         <span style='color: #c0c0c0; font-size:18px;margin-left:10px'>{createtime.strftime("%Y-%m-%d %H:%M:%S")}</span>         
    </div>"""
    return (message)


def get_agent_reply_msg_content_formatted(content):
    message = f"""{content}"""
    return (message)


def add_agent_reply_msg_to_message_window(browser_page, content):
    if content:

        message = content

        text = message

        # 使用正则表达式提取Python代码块
        python_code_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
        python_code_matches = python_code_pattern.findall(text)

        # 打印提取的Python代码块
        python_code_list = []

        for code_block in python_code_matches:
            python_code_list.append(code_block.strip())

        # 打印结果
        print("Python代码列表:")
        i = 0
        s = text

        answer_list = []
        type_list = []
        for code in python_code_list:
            print("python_code_list length", len(python_code_list))
            print("i:", i)
            print(code)

            substring = code
            left_part = s[:s.find(substring)]
            right_part = s[s.find(substring) + len(substring):]
            print("左边所有字符:", left_part)
            print("右边所有字符:", right_part)

            left_part = left_part[:left_part.find("```python")]
            right_part = right_part[right_part.find("```") + len("```"):]
            s = right_part
            answer_list.append(left_part.strip())
            type_list.append(0)
            answer_list.append(code)
            type_list.append(1)

            i += 1
            if len(python_code_list) == i:
                answer_list.append(right_part.strip())
                type_list.append(0)

        print("show all list *************************")
        j = 0
        scriptStr = ""
        if len(answer_list) > 0:
            for answer in answer_list:
                print("*******", j, "***********")
                print("type_list:", type_list[j])

                if type_list[j] == 1:

                    copyhtml = """<div style="margin-top:15px;border:solid 0px red;width:100%;overflow: hidden; ">
                            <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">代码类型:Python</span>
                            <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
                        </div>""".format(j, j)
                else:
                    copyhtml = """<div style="border:solid 0px red;width:100%;overflow: hidden;display:none ">
                            <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">Python</span>
                            <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
                        </div>""".format(j, j)

                print("copyhtml:", copyhtml)
                browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += `' + copyhtml + '<br><br>`')

                print(answer)
                message = answer

                if type_list[j] == 1:
                    browser_page.runJavaScript("document.getElementById('allcontent').innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy" + str(j) + "' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
                else:
                    browser_page.runJavaScript("document.getElementById('allcontent').innerHTML += " + "\"<pre id='codeToCopy" + str(j) + "' style='margin-top:-50px;border:solid 0px #c0c0c0;width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word;' class='language-python'></pre>\"")

                message = message.replace('`', '\\`')
                message = f"""`{message}`"""
                browser_page.runJavaScript("$('#codeToCopy" + str(j) + "').html(" + message + ");")
                browser_page.runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy" + str(j) + "'));")

                # browser_page.runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
                # browser_page.runJavaScript("$('#codeToCopy').html(" + message + ");")
                # #browser_page.runJavaScript("hljs.highlightAll();")
                # browser_page.runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy'));")#$('#codeToCopy')

                scriptStr = scriptStr + """
    document.getElementById('copyCodeLink{}').addEventListener('click', function (e) {{
        e.preventDefault();
        copyCode{}();
    }});

    function copyCode{}() {{
        var code = document.getElementById('codeToCopy{}');
        var range = document.createRange();
        range.selectNode(code);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        document.execCommand('copy');
        window.getSelection().removeAllRanges();
        $("#yifuzhi{}").show();
        setTimeout(function () {{
        $("#yifuzhi{}").hide();
    }}, 1500);
    }}""".format(j, j, j, j, j, j)
                print("scripts:", scriptStr)
                # browser_page.runJavaScript('document.body.innerHTML += `' + message + '<br><br>`')

                j += 1
        else:
            browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += `<pre style="width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word; ">' + message + '</pre><br>`')
        if scriptStr != "":
            browser_page.runJavaScript(scriptStr)


def toggle_msg_loading_status(browser_page):
    stoploadingstript = "var images = document.getElementsByClassName('imgcls');for (var i = 0; i < images.length; i++) { images[i].style.display = 'none';}"
    browser_page.runJavaScript(stoploadingstript)


# Common
def generate_random_id():
    # 生成随机字母ID，使用大写字母
    random_id = ''.join(random.choices(string.ascii_uppercase, k=2))
    # 获取当前时间

    current_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    # 生成随机数
    random_number = ''.join(random.choices(string.digits, k=5))
    # 组合生成的ID
    generated_id = random_id + current_time + random_number
    return generated_id


def image_to_base64(image_path):
    # 检查文件是否存在
    if not os.path.isfile(image_path):
        return "错误：文件不存在"

    # 检查文件是否为图片
    if not image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        return "错误：文件不是图片"

    try:
        with open(image_path, "rb") as image_file:
            # 读取文件内容并编码为Base64
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        return f"错误：{str(e)}"


def generate_img_tag(image_path):
    base64_string = image_to_base64(image_path)
    if "错误" not in base64_string:  # 确保没有错误信息
        # 生成<img>标签
        img_tag = f'<img src="data:image/jpeg;base64,{base64_string}" alt="Image" />'
        return img_tag
    else:
        return base64_string  # 返回错误信息


def get_content_from_attachment_content_list(attachment_content_list):
    # 初始化文档内容和图像内容列表
    doc_content = ""
    retrieve_doc_content = ""
    attachment_image_list = []

    # 遍历所有的附件内容
    for content_type, value_1, value_2 in attachment_content_list:
        if content_type == "document":
            # 处理文档类型
            doc_content += "\n" + value_1
        elif content_type == "image":
            # 处理图片类型
            img_base64 = value_1  # 假设 value 是 base64 编码的图像数据
            attachment_image_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
            })
        elif content_type == "km":
            # 处理文档类型
            retrieve_doc_content += "\n" + value_1

    return doc_content, attachment_image_list, retrieve_doc_content


def download_image(url, save_path):
    try:
        # 发送HTTP请求下载图片
        response = requests.get(url)
        response.raise_for_status()  # 如果请求不成功，抛出HTTPError

        # 保存图片到本地
        with open(save_path, 'wb') as file:
            file.write(response.content)

        print(f"Image successfully downloaded: {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")

def open_file( file_path):
    if sys.platform == "win32":
        os.startfile(file_path)
    elif sys.platform == "darwin":
        subprocess.call(("open", file_path))
    else:
        subprocess.call(("xdg-open", file_path))


def extract_json_string_from_llm(input_string):
    """
    从输入字符串中提取位于三个反引号之间的内容

    参数:
    input_string (str): 包含反引号的字符串

    返回:
    str: 提取的字符串，如果未找到则返回空字符串
    """
    # 使用正则表达式匹配反引号之间的内容
    match = re.search(r'```json(.*?)```', input_string, re.DOTALL)

    if match:
        # 返回匹配到的字符串，并去掉前后的空白字符
        return match.group(1).strip()
    else:
        # 如果没有找到，则返回空字符串
        return ""
