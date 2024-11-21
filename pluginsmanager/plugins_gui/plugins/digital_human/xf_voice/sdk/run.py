import json

img_dic = {
    "code": 1,
    "msg": "success",
    "data": {
        "owner": "cp13c68b",
        "count": 2,
        "hiresfix": False,
        "ownerid": "715ef38a835a44c89590f7853d8ab8f4",
        "steps": 20,
        "seed": -1,
        "checkpoint": "chilloutmix_NiPrunedFp32Fix.safetensors [75e19d71e2]",
        "batchsize": 1,
        "samplername": "Euler a",
        "prompt": "<lora:aki:1>1cat",
        "niter": 1,
        "createtime": "2023-07-17T16:29:55.978151",
        "lora": "aki",
        "cfgscale": 7,
        "nprompt": "",
        "restorefaces": False,
        "id": 9,
        "width": 512,
        "tiling": False,
        "height": 512,
        "aipicture_tmp": [
            {
                "name": "pic_20230717162959_1.png",
                "remark": "<lora:aki:1>1cat\nSteps: 20, Sampler: Euler a, CFG scale: 7.0, Seed: 3335316263, Size: 512x512, Model hash: 75e19d71e2, Model: chilloutmix_NiPrunedFp32Fix, Seed resize from: -1x-1, Denoising strength: 0, Lora hashes: \"aki: 80526487575f\", Version: v1.3.2",
                "size": 371,
                "urllink": "data\\cp13c68b\\tmp\\pic_20230717162959_1.png",
                "ownerid": "715ef38a835a44c89590f7853d8ab8f4",
                "md5name": "123"
            },
            {
                "name": "pic_20230717162959_2.png",
                "remark": "<lora:aki:1>1cat\nSteps: 20, Sampler: Euler a, CFG scale: 7.0, Seed: 3335316264, Size: 512x512, Model hash: 75e19d71e2, Model: chilloutmix_NiPrunedFp32Fix, Seed resize from: -1x-1, Denoising strength: 0, Lora hashes: \"aki: 80526487575f\", Version: v1.3.2",
                "size": 426,
                "urllink": "data\\cp13c68b\\tmp\\pic_20230717162959_2.png",
                "ownerid": "715ef38a835a44c89590f7853d8ab8f4",
                "md5name": "123"
            }
        ]
    }
}

ss = str(img_dic)
print(ss)
obj_str =  json.dumps(img_dic)
obj = json.loads(obj_str)
print(len(obj["data"]["aipicture_tmp"]))


# print(ast.literal_eval(img_dic))
