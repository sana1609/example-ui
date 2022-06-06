from github import Github
import base64
import requests
import re
from tabulate import tabulate
from sql_metadata import Parser


def processString(txt):
    specialchars = ["'", "`", ";", ")"]
    for specialchar in specialchars:
        txt = txt.replace(specialchar, '')
    return txt


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


def url_extractor(methods_in, method_in):
    global url_out
    if ".get" in methods_in[0]:
        url_out = method_in.split(".get(")
        if len(url_out) == 1:
            url_out = method_in.split(".get (")
    elif ".put" in methods_in[0]:
        url_out = method_in.split(".put(")
        if len(url_out) == 1:
            url_out = method_in.split(".put (")
    elif ".delete" in methods_in[0]:
        url_out = method_in.split(".delete(")
        if len(url_out) == 1:
            url_out = method_in.split(".delete (")
    elif ".post" in methods_in[0]:
        url_out = method_in.split(".post(")
        if len(url_out) == 1:
            url_out = method_in.split(".post (")
    elif ".patch" in methods_in[0]:
        url_out = method_in.split(".patch(")
        if len(url_out) == 1:
            url_out = method_in.split(".patch (")
    else:
        pass
    return url_out


def query_extractor(query_in):
    global table_out, query_out
    if len(query_in) > 1:
        # extracting db queries
        query_select = re.findall("select .*?;", query_in[1])
        query_delete = re.findall("delete .*?;", query_in[1])
        query_insert = re.findall("insert into.*?;", query_in[1])
        query_drop = re.findall("drop table.*?;", query_in[1])
        query_update = re.findall("update .*?;", query_in[1])
        query_alter = re.findall("alter table.*?;", query_in[1])
        query_create = re.findall("create table.*?;", query_in[1])
        query_truncate = re.findall("truncate table.*?;", query_in[1])
        queries = query_select + query_delete + query_insert + query_drop + query_update + query_alter + query_create + query_truncate
        if len(queries) == 0:
            # extracting db queries
            query_select = re.findall("select .*?,", query_in[1])
            query_delete = re.findall("delete .*?,", query_in[1])
            query_insert = re.findall("insert into.*?,", query_in[1])
            query_drop = re.findall("drop table.*?,", query_in[1])
            query_update = re.findall("update .*?,", query_in[1])
            query_alter = re.findall("alter table.*?,", query_in[1])
            query_create = re.findall("create table.*?,", query_in[1])
            query_truncate = re.findall("truncate table.*?,", query_in[1])
            queries_sql = query_select + query_delete + query_insert + query_drop + query_update + query_alter + query_create + query_truncate
            if len(queries_sql) != 0:
                # query cleaning
                queries_sql[0] = processString(queries_sql[0])
                table_out = Parser(queries_sql[0]).tables
                query_out = queries_sql[0]
        else:
            if len(queries) != 0:
                # query cleaning
                queries[0] = processString(queries[0])
                table_out = Parser(queries[0]).tables
                query_out = queries[0]
    else:
        query_out = None
        table_out = None

    return query_out, table_out


def get_api_linked_files(git_url, git_token):
    global text
    js_files, repo_name = get_files(url=git_url, access_token=git_token)
    matched_files = []

    for file in js_files:
        file_name = file.split('/')
        if file_name[-1] != 'serviceWorker.js' and file_name[-1] != 'serviceworker.js':
            contents = get_file_contents(repository_name=repo_name, file_name=file,
                                         token=git_token)
            # removing escape characters
            bad_chars = ['\t', '\n']
            for i in bad_chars:
                text = contents.replace(i, '')
            # extracting text that contains http method and url
            text = text.lower()
            urls_put = re.findall(".put\\s*\\(.*?}\\)", text)
            urls_get = re.findall(".get\\s*\\(.*?}\\)", text)
            urls_delete = re.findall(".delete\\s*\\(.*?}\\)", text)
            urls_patch = re.findall(".patch\\s*\\(.*?}\\)", text)
            urls_post = re.findall(".post\\s*\\(.*?}\\)", text)
            urls_db = urls_put + urls_get + urls_delete + urls_patch + urls_post
            for method in urls_db:
                methods = method.split("(")
                url = url_extractor(methods_in=methods, method_in=method)
                for url_single in url:
                    query_extracted = url_single.split(",", 1)
                    final_query, final_table = query_extractor(query_extracted)
                    if final_query is not None or final_table is not None:
                        matched_files.append([file, methods[0], query_extracted[0], final_query, final_table])
    # modifying method names
    for method in matched_files:
        method[1] = [keyword.upper() for keyword in ["post", "patch", "put", "delete", "get"] if
                     keyword in method[1].lower()][0]
    return matched_files

    # tabulate the summary log


# getting api calling files
api_linked_files = get_api_linked_files(git_url="https://github.com/sana1609/open-online-api2",
                                        git_token="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")
# formatting and visualising aoi linked files
if type(api_linked_files) is dict:
    print(api_linked_files)
else:
    col_names = ["File_name", "Method", "URL", "query", "table"]
    print(tabulate(api_linked_files, headers=col_names, tablefmt='psql'))
