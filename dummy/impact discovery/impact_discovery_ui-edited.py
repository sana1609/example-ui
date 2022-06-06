#
# Copyright 2022 - Atos Group
#
# you may not use this file except in compliance with the Atos License.
# --------------------------------------------------------------------------
# File name : impact_discovery_ui_edited.py
# Application name : Impact_discovery
# File definition : Find API impacted files in UI
# Project name : AMS - Digital Assurance Platform
# File owner : sana-venkata.sudhakar@atos.net
# File created by : sana-venkata.sudhakar@atos.net
# File creation date :
# Build version : 202205 V1.0.0
# --Version Control
# V1.0.0 - First version of Impact_discovery

# ---------------------------------------------------------------------------

# Importing packages
from flask import Flask, request
from github import Github
import base64
import requests
import re
import pandas as pd


# User defined exceptions
class RateLimitReachedError(Exception):
    pass


class EmptyRepositoryError(Exception):
    pass


class RepositoryNotFoundError(Exception):
    pass


class BadCredentialsError(Exception):
    pass


class NoJavaScriptFilesPresentError(Exception):
    pass


class NoMethodsBeingCalled(Exception):
    pass


# A function to get file contents present in github repository by using github api
def get_file_contents(repository_name, file_name, token):
    try:
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
            if "API rate limit exceeded" in str(req.json()):
                return {"error encountered": "API rate limit exceeded"}
    except Exception as e:
        e = str(e)
        return {"error encountered": e}


class ImpactDiscoveryUi:
    """Impact discovery ui class used to find files that calling API, API methods and urls that are used to call API.

                Parameters
                ----------
                git_repo_url : string
                    Github repository url where the code is present
                git_personal_token : string
                    Github personal access token to get access to the github account

                Returns
                -------
                Summary log
                    A summary log consists of file name, method being used, url of API and description of method
        """

    # constructor
    def __init__(self, git_repo_url, git_personal_token):
        self.git_repo_url = git_repo_url
        self.git_personal_token = git_personal_token

    # getting all files present in repository
    def get_files(self):
        try:
            git_repo_url = self.git_repo_url
            git_personal_token = self.git_personal_token
            split = git_repo_url.split("/", 3)
            # extract repository name
            repository_name = split[3]
            # generating github object using access token
            g = Github(login_or_token=git_personal_token)
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
            return [js_files_extracted, repository_name]
        except Exception as e:
            return [str(e)]

    def get_api_linked_files(self):
        try:
            git_personal_token = self.git_personal_token
            global text
            get_files = ImpactDiscoveryUi.get_files(self)
            if len(get_files) == 1:
                if "Not Found" in get_files[0]:
                    raise RepositoryNotFoundError
                elif "This repository is empty" in get_files[0]:
                    raise EmptyRepositoryError
                elif "Bad credentials" in get_files[0]:
                    raise BadCredentialsError
                else:
                    return {"error encountered": get_files[0]}
            else:
                js_files = get_files[0]
                repo_name = get_files[1]
                matched_files = []
                if len(js_files) == 0:
                    raise NoJavaScriptFilesPresentError
                else:
                    for file in js_files:
                        file_name = file.split('/')
                        if file_name[-1] != 'serviceWorker.js' and file_name[-1] != 'serviceworker.js':
                            contents = get_file_contents(repository_name=repo_name, file_name=file,
                                                         token=git_personal_token)
                            if type(contents) is dict:
                                raise RateLimitReachedError
                            else:
                                # removing escape characters
                                bad_chars = ['\t', '\n']
                                for i in bad_chars:
                                    text = contents.replace(i, '')
                                # extracting text that contains http method and url which using axios method
                                ui_urls_put = re.findall(".put\\(.*?\\)", text)
                                ui_urls_get = re.findall(".get\\(.*?\\)", text)
                                ui_urls_delete = re.findall(".delete\\(.*?\\)", text)
                                ui_urls_patch = re.findall(".patch\\(.*?\\)", text)
                                ui_urls_post = re.findall(".post\\(.*?\\)", text)
                                ui_urls_fetch_get = re.findall("fetch\\(.*?\\)", contents)

                                urls_axios = ui_urls_put + ui_urls_get + ui_urls_delete + ui_urls_patch + ui_urls_post + ui_urls_fetch_get
                                for v in urls_axios:
                                    method = v.split("(")
                                    if len(method) > 1:
                                        for i in range(len(method)):
                                            if "http" in method[i]:
                                                if ")" in method[i]:
                                                    url = method[i].split(")")
                                                    matched_files.append([file, method[i - 1], url[0]])
                                                else:
                                                    matched_files.append([file, method[i - 1], method[i]])
                                # extracting text that contains http method and url which using fetch method
                                text = text.lower()
                                urls_fetch = re.findall("fetch\\(.*?;", text)
                                fetch_files = []
                                for v in urls_fetch:
                                    method = v.split("fetch")
                                    for i in method:
                                        if "method" in i:
                                            fetch_files.append(i)
                                for i in fetch_files:
                                    res = i.split(",", 1)
                                    if len(res) == 2:
                                        matched_files.append([file, res[1], res[0]])
                    # modifying method names and adding description
                    for method in matched_files:
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
                    return matched_files
        except RateLimitReachedError:
            return {"error encountered": "API rate limit exceeded"}
        except EmptyRepositoryError:
            return {"error encountered": "This repository is empty"}
        except RepositoryNotFoundError:
            return {"error encountered": "Repository is not found"}
        except NoJavaScriptFilesPresentError:
            return {"error encountered": "There is no Java Script files present given repository"}
        except BadCredentialsError:
            return {"error encountered": "Bad Credentials, the token given is not valid"}
        except Exception as e:
            e = str(e)
            return {"error encountered": e}


# Flask operation starts here
app = Flask(__name__)


@app.route('/impact_discovery', methods=["POST"])
def impact_discovery():
    try:
        git_repo_url = request.form["git_repo_url"]
        git_access_token = request.form["git_access_token"]
        impact_discovery_ui = ImpactDiscoveryUi(git_repo_url, git_access_token)

        api_linked_files = impact_discovery_ui.get_api_linked_files()
        api_linked_files_final = pd.DataFrame(data=api_linked_files, columns=["File_name", "Method",
                                                                              "URL"])
        if len(api_linked_files_final) != 0:
            if isinstance(api_linked_files, dict):
                return api_linked_files
            else:
                return api_linked_files_final.to_json(indent=4, orient='records')
        else:
            raise NoMethodsBeingCalled

    except NoMethodsBeingCalled:
        return {"error encountered": "API methods are not being called"}
    except Exception as e:
        e = str(e)
        return {"error encountered": e}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
