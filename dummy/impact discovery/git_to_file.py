import base64

import requests

url = "https://api.github.com/repos/sana1609/sample-crud/contents/src/Components/Edit.js"
req = requests.get(url)
if req.status_code == requests.codes.ok:
    req = req.json()  # the response is a JSON
    # req is now a dict with keys: name, encoding, url, size ...
    # and content. But it is encoded with base64.
    content = base64.b64decode(req['content'])
    with open("edit.js", "w") as f:
        f.write(content.decode())
        print("over")
    f.close()
else:
    print(req)
with open("edit.js", "r") as f:
    data = f.read()
f.close()


def findall(text, sub):
    result = []
    k = 0
    while k < len(text):
        k = text.find(sub, k)
        if k == -1:
            return result
        else:
            result.append(k)
            k += 1
    return result


list = findall(data, ".get(")
