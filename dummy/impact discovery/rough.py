import re
from tabulate import tabulate
from sql_metadata import Parser


def result(contents):
    global text, url, combined
    bad_chars = ['\t', '\n']
    for i in bad_chars:
        text = contents.replace(i, '')

    matched_files = []
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
                    print(queries_sql)
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
                        matched_files.append([methods[0], combined[0], queries[0], tables])
                        print(len(matched_files))
    if len(urls_axios) == 0:
        print("hi")
        query_select = re.findall("select .*?;", text)
        query_delete = re.findall("delete .*?;", text)
        query_insert = re.findall("insert .*?;", text)
        query_drop = re.findall("drop .*?;", text)
        query_update = re.findall("update .*?;", text)
        queries = query_select + query_delete + query_insert + query_drop + query_update
        print(queries)
        if len(queries) == 0:
            query_select = re.findall("select .*?,", text)
            query_delete = re.findall("delete .*?,", text)
            query_insert = re.findall("insert .*?,", text)
            query_drop = re.findall("drop .*?,", text)
            query_update = re.findall("update .*?,", text)
            queries_sql = query_select + query_delete + query_insert + query_drop + query_update
            print(queries_sql)
            if len(queries_sql) != 0:
                for query in queries_sql:
                    query = query.replace('"', "")
                    query = query.replace("'", "")
                    query = query.replace("`", "")
                    query = query.replace(";", "")
                    query = query.replace(")", "")
                    # columns = Parser(final_query[0]).columns
                    tables = Parser(query).tables
                    matched_files.append([query, tables])
        else:
            if len(queries) != 0:
                for query in queries:
                    query = query.replace('"', "")
                    query = query.replace("'", "")
                    query = query.replace("`", "")
                    query = query.replace(";", "")
                    query = query.replace(")", "")
                    # columns = Parser(final_query[0]).columns
                    tables = Parser(query).tables
                    matched_files.append([query, tables])
    print(matched_files)
    return matched_files


def data_formatting(file):
    # modifying method names and adding description
    # for method in file:
    #     if "post" in method[0].lower():
    #         method[0] = "POST"
    #
    #     elif "patch" in method[0].lower():
    #         method[0] = "PATCH"
    #
    #     elif "put" in method[0].lower():
    #         method[0] = "PUT"
    #
    #     elif "delete" in method[0].lower():
    #         method[0] = "DELETE"
    #
    #     elif "get" in method[0].lower():
    #         method[0] = "GET"
    #
    #     elif "fetch" in method[0].lower():
    #         method[0] = "GET"
    #
    #         continue

    # tabulate the summary log
    col_names = ["Query", "Table" ]
    print(tabulate(file, headers=col_names, tablefmt='psql'))


with open("../learning/impact discovery/data2.txt", "r") as f:
    contents = f.read()
    f.close()
data_formatting(result(contents))
