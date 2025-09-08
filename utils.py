from takeprompt import BedrockAgent
import json 
import re 
from typing import List, Dict, Any, Union, Optional, Tuple

def format_dict_string(unformated_str: str) -> str:
    """Format improper dictionary string into proper dict string using Bedrock"""
    try:
        print("inside")
        ss1=unformated_str.replace("```",'')
        ss = re.sub(r'\s+', ' ', ss1)
        ss1=ss.replace(" \"",'"')
        ss2=ss1.replace("\" ",'"')
        for ig in range(len(ss2)):
            if ss2[ig] == '{':
                break
        for ik in range(len(ss2)-1,0,-1):
            if ss2[ik] == '}':
                break
        ss = ss2[ig:ik]
        res_out = json.loads(ss)
        # if not len(re.findall(r'{', ss)) == len(re.findall(r'}', ss)):
        #     d_count = len(re.findall(r'{', ss)) - len(re.findall(r'}', ss))
        #     for kl in range(d_count):
        #         ss+='}'
    except Exception as e:
        print(f"Exception occured: {e}")
        return ss+'}'
        # print(str(e))
        # print("******************")
        # if "Expecting" in str(e) and "delimiter" in str(e):
        #     ew=str(e).split('(char ')[-1]
        #     ss=ss2[:int(ew[:-1])-1]+ss2[int(ew[:-1])+1:]
    
    return res_out
