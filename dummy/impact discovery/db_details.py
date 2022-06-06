from github import Github
import base64
import requests
import re
from tabulate import tabulate
from sql_metadata import Parser


# getting all files present in repository
def get_files(url, access_token):
    split = url.split("/", 3)
    repository_name = split[3]
    # generating github object using access token
    g = Github(login_or_token=access_token)
    files = []
    repo = g.get_repo(repository_name)
    # all files in repo
    files_extracted = repo.get_contents("")
    while files_extracted:
        file = files_extracted.pop(0)
        if file.type == "dir":
            files_extracted.extend(repo.get_contents(file.path))
        else:
            files.append(file.path)
    js_files_extracted = []
    # extracting javascript files from all files
    for file in files:
        extension = file.split('.')
        if extension[-1] == 'js' or extension[-1] == 'jsx':
            js_files_extracted.append(file)
    return js_files_extracted, repository_name


# getting file contents present in each each file
def get_file_contents(repository_name, file_name, token):
    authorization = f'token {token}'
    headers = {
        "Authorization": authorization,
    }
    url = "https://api.github.com/repos/" + repository_name + "/contents/" + file_name
    req = requests.get(url=url, headers=headers)
    if req.status_code == requests.codes.ok:
        req = req.json()  # the response is a JSON
        # req is now a dict with keys: name, encoding, url, size ...
        # and content. But it is encoded with base64.
        content = base64.b64decode(req['content'])
        return content.decode()
    else:
        return req.json()


def get_api_linked_files(git_url, git_token):
    global text, url
    js_files, repo_name = get_files(url=git_url, access_token=git_token)
    matched_files = []

    for file in js_files:
        file_name = file.split('/')
        if file_name[-1] != 'serviceWorker.js' and file_name[-1] != 'serviceworker.js':
            contents = get_file_contents(repository_name=repo_name, file_name=file, token=git_token)
            if type(contents) is dict:
                return contents
            else:
                # removing escape characters
                bad_chars = ['\t', '\n']
                for i in bad_chars:
                    text = contents.replace(i, '')
                # extracting text that contains http method and url
                text = text.lower()
                ui_urls_put = re.findall(".put\\s*\\(.*?}\\);", text)
                ui_urls_get = re.findall(".get\\s*\\(.*?}\\);", text)
                ui_urls_delete = re.findall(".delete\\s*\\(.*?}\\);", text)
                ui_urls_patch = re.findall(".patch\\s*\\(.*?}\\);", text)
                ui_urls_post = re.findall(".post\\s*\\(.*?}\\);", text)
                urls_axios = ui_urls_put + ui_urls_get + ui_urls_delete + ui_urls_patch + ui_urls_post
                [print(x) for x in urls_axios]
                for method in urls_axios:
                    methods = method.split("(")
                    if ".get" in methods[0]:
                        url = method.split(".get(")
                        if len(url) == 1:
                            url = method.split(".get (")
                    elif ".put" in methods[0]:
                        url = method.split(".put(")
                        if len(url) == 1:
                            url = method.split(".put (")
                    elif ".delete" in methods[0]:
                        url = method.split(".delete(")
                        if len(url) == 1:
                            url = method.split(".delete (")
                    elif ".post" in methods[0]:
                        url = method.split(".post(")
                        if len(url) == 1:
                            url = method.split(".post (")
                    elif ".patch" in methods[0]:
                        url = method.split(".patch(")
                        if len(url) == 1:
                            url = method.split(".patch (")
                    else:
                        pass
                    for url_single in url:
                        combined = url_single.split(",", 1)
                        if len(combined) > 1:
                            print(combined[1])
                            query_select = re.findall("select .*?;", combined[1])
                            query_delete = re.findall("delete .*?;", combined[1])
                            query_insert = re.findall("insert .*?;", combined[1])
                            query_drop = re.findall("drop .*?;", combined[1])
                            query_update = re.findall("update .*?;", combined[1])
                            queries = query_select + query_delete + query_insert + query_drop + query_update
                            print(queries)
                            if len(queries) == 0:
                                query_select = re.findall("select .*?,", combined[1])
                                query_delete = re.findall("delete .*?,", combined[1])
                                query_insert = re.findall("insert .*?,", combined[1])
                                query_drop = re.findall("drop .*?,", combined[1])
                                query_update = re.findall("update .*?,", combined[1])
                                queries_sql = query_select + query_delete + query_insert + query_drop + query_update
                                if len(queries_sql) != 0:
                                    queries_sql[0] = queries_sql[0].replace('"', "")
                                    queries_sql[0] = queries_sql[0].replace("'", "")
                                    queries_sql[0] = queries_sql[0].replace("`", "")
                                    queries_sql[0] = queries_sql[0].replace(";", "")
                                    queries_sql[0] = queries_sql[0].replace(")", "")
                                    # columns = Parser(final_query[0]).columns
                                    tables = Parser(queries_sql[0]).tables
                                    matched_files.append([methods[0], combined[0], queries_sql[0], tables])
                            else:
                                if len(queries) != 0:
                                    queries[0] = queries[0].replace('"', "")
                                    queries[0] = queries[0].replace("'", "")
                                    queries[0] = queries[0].replace("`", "")
                                    queries[0] = queries[0].replace(";", "")
                                    queries[0] = queries[0].replace(")", "")
                                    # columns = Parser(final_query[0]).columns
                                    tables = Parser(queries[0]).tables
                                    matched_files.append([file, methods[0], combined[0], queries[0], tables])

    return matched_files


def data_formatting(file):
    for method in file:
        if "post" in method[1].lower():
            method[1] = "POST"
        elif "patch" in method[1].lower():
            method[1] = "PATCH"
        elif "put" in method[1].lower():
            method[1] = "PUT"
        elif "delete" in method[1].lower():
            method[1] = "DELETE"
        elif "get" in method[1].lower():
            method[1] = "GET"
        elif "fetch" in method[1].lower():
            method[1] = "GET"
        else:
            continue
    col_names = ["File_name", "Method", "URL", "Query", "Table_name"]
    print(tabulate(file, headers=col_names, tablefmt='psql'))


# getting api calling files
api_linked_files = get_api_linked_files(git_url="https://github.com/sana1609/delete",
                                        git_token="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")
# formatting and visualising aoi linked files
if type(api_linked_files) is dict:
    print(api_linked_files)
else:
    data_formatting(api_linked_files)
