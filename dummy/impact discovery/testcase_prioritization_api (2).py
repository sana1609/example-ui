#
# Copyright 2021 - Atos Group
#
# you may not use this file except in compliance with the Atos License.
# --------------------------------------------------------------------------
# File name : testcase_prioritization_api.py
# Application name : Testcase_prioritization
# File definition : Prioritizing test cases and ranking test cases within each priority
# Project name : AMS - Digital Assurance Platform
# File owner : rajalakshmi.r@atos.net
# File created by : rajalakshmi.r@atos.net
# File creation date : 06-12-2021
# Build version : 202112 V1.0.0
# --Version Control
# V1.0.0 - First version of test prioritization

# ---------------------------------------------------------------------------


# Importing packages
import numpy as np
import pandas as pd
import os
import json
from werkzeug.utils import secure_filename
import warnings
import janitor
from sklearn.cluster import KMeans
from string import punctuation
from flask import Flask, request
from scipy.stats import zscore


warnings.filterwarnings("ignore")


# User defined exceptions
class RecordsEmptyError(Exception):
    pass


class FileFormatError(Exception):
    pass


class ColumnDoesNotExistError(Exception):
    pass


# Treating outliers
def remove_outlier(col):
    sorted(col)
    q1, q3 = np.percentile(col, [25, 75])
    iqr = q3 - q1
    lower_range = q1-(1.5 * iqr)
    upper_range = q3+(1.5 * iqr)
    return lower_range, upper_range


class TestCasePriority:
    """Test case priority class used to prioritize test cases based on derived weights.

                Parameters
                ----------
                file, req_weight, sprint, execution_status, defect_sev, complexity, time,
                 defects_count, test_case
                file : string(file path)
                    The source dataframe to serve as a basis for deriving priority of test cases.
                req_weight : string
                    weightage of requirements
                sprint : string
                    sprint/release in which the test case has been executed
                execution_status : string
                    whether a test case has passed or failed in each run
                defect_sev : string
                    Severity of defects linked to the test cases
                complexity : string
                    whether multiple system dependencies are required to run a test case
                time : string
                    total number of days required to execute a test case
                defects_count : string
                    Number of defects logged while executing a test case
                test_case : string
                    Name of the test case for which the priority needs to be derived based
                    on other parameters

                Returns
                -------
                Prioritized cases
                    Recommended priority of test cases and ranking of each test cases within each priority
                    are derived based on the weightage of input parameters
        """

    # constructor
    def __init__(self, file, req_weight, sprint, execution_status, defect_sev, complexity, time,
                 defects_count, test_case):
        self.file = file
        self.req_weight = req_weight
        self.sprint = sprint
        self.execution_status = execution_status
        self.defect_sev = defect_sev
        self.complexity = complexity
        self.time = time
        self.defects_count = defects_count
        self.test_case = test_case

    def priority_clusters(self):
        try:
            file = self.file
            req_weight = self.req_weight
            sprint = self.sprint
            execution_status = self.execution_status
            defect_sev = self.defect_sev
            complexity = self.complexity
            time = self.time
            defects_count = self.defects_count
            test_case = self.test_case

            file = file.filename
            split_tup = os.path.splitext(file)

            file_extension = split_tup[1]  # extract the file extension
            if file_extension == ".csv":
                df = pd.read_csv(file)
            elif file_extension in [".xlsx", ".xls"]:
                df = pd.read_excel(file)
            else:
                raise FileFormatError

            # Preprocessing column names
            df = df.clean_names()
            df.columns = df.columns.str.strip(punctuation)
            df[sprint].astype(str)
            if {req_weight, sprint, execution_status, defect_sev, complexity, time, defects_count, test_case}.issubset(df.columns):
                if not df.empty:
                    df_param = df[
                        [req_weight, sprint, execution_status, defect_sev, complexity, time, defects_count, test_case]]
                    df_agg = df_param.groupby(test_case).agg({req_weight: 'max', defect_sev: 'max', complexity: 'max',
                                                              time: 'mean', defects_count: 'mean',
                                                              execution_status: lambda x: ','.join(x),
                                                              sprint: 'count'}).reset_index()
                    df_agg[time] = round(df_agg[time], 2)
                    df_agg.drop_duplicates(inplace=True)
                    df_agg['S.No'] = np.arange(len(df_agg))

                    # Calculating pass percent
                    df_agg['Execn_status'] = df_agg[execution_status]
                    df_agg['Execn_status'] = df_agg['Execn_status'].str.replace(",", "")
                    df_agg['Pass_percent'] = (df_agg['Execn_status'].str.count('P')) / df_agg[
                        'Execn_status'].str.len() * 100
                    df_agg['Pass_percent'] = round(df_agg['Pass_percent'], 2)

                    df_subset = df_agg[['S.No', req_weight, defect_sev, 'Pass_percent', complexity, time, defects_count,
                                        test_case, sprint]]

                    # Converting data type of time
                    df_subset[time].astype(int)
                    # df_subset=df_subset_1.copy()
                    # Treating outliers
                    cont = ['Pass_percent', time, defects_count]
                    for x in cont:
                        lowerrange_parameter, upperrange_parameter = remove_outlier(df_subset[x])
                        df_subset[x] = np.where(df_subset[x] > upperrange_parameter, upperrange_parameter, df_subset[x])
                        df_subset[x] = np.where(df_subset[x] < lowerrange_parameter, lowerrange_parameter, df_subset[x])

                    # Creating copy of df_subset
                    df_copy = df_subset.copy()

                    # Standardize the data before clustering
                    df_copy[['Pass_percent', time, defects_count]] = df_copy[['Pass_percent', time, defects_count]].apply(zscore)

                    # One-hot-encode the categorical columns by applying get dummies
                    df_ohe = pd.get_dummies(data=df_copy, columns=[req_weight, sprint, defect_sev, complexity])

                    # Dataframe subset to apply kmeans algorithm
                    df_kmeans = df_ohe.drop(columns=["S.No", test_case])

                    # applying kmeans alogoritm
                    clusters = KMeans(n_clusters=3, n_init=25, max_iter=600, random_state=0).fit_predict(df_kmeans)

                    # Merging cluster IDs with main dataframe
                    df_copy['cluster'] = list(clusters)

                    # Combining cluster IDs with scaled dataset
                    df_subset_cluster = df_copy[['S.No', req_weight, defect_sev, complexity, test_case, 'cluster']]

                    # Merging the cluster IDs with the original dataset
                    df_cluster_merge = pd.merge(df_subset, df_subset_cluster, how='inner',
                                                on=['S.No', req_weight, defect_sev, complexity, test_case])

                    del df_param, df_agg, df_subset, df_subset_cluster, df_copy
                    # Identify cluster patterns

                    # Total cluster pattern
                    df_cluster_pattern = df_cluster_merge.groupby('cluster').mean()
                    df_cluster_pattern['freq_agg'] = df_cluster_merge.cluster.value_counts().sort_index()

                    # Mapping cluster ID
                    df_cluster_pattern['cluster'] = [0, 1, 2]

                    # Calculate the weighed score based on all parameters
                    df_cluster_pattern['Cluster_score'] = df_cluster_pattern[sprint] + df_cluster_pattern[defects_count] + df_cluster_pattern[complexity] - df_cluster_pattern['Pass_percent'] + df_cluster_pattern[time] - (5 * df_cluster_pattern[defect_sev]) - (5 * df_cluster_pattern[req_weight])
                    df_priority = df_cluster_pattern.sort_values(['Cluster_score'], ascending=False)
                    df_priority['Recommended_Priority'] = ['High', 'Medium', 'Low']

                    # Creating subset with cluster and priority labels
                    df_priority_subset = df_priority[['cluster', 'Recommended_Priority']]
                    df_priority_subset.reset_index(drop=True, inplace=True)

                    # Aggregate of test case
                    count_series_tc = df_cluster_merge.groupby(
                        ['S.No', req_weight, 'Pass_percent', defect_sev, complexity, time, defects_count, 'cluster',
                         sprint]).agg({test_case: lambda x: ','.join(set(x))}).reset_index()

                    # Calculating scores of each element within each cluster
                    count_series_tc['Weighed_Score'] = count_series_tc[sprint] + count_series_tc[defects_count] + count_series_tc[complexity] - count_series_tc['Pass_percent'] + count_series_tc[time] - (5 * count_series_tc[defect_sev]) - (5 * count_series_tc[req_weight])
                    count_series_tc.reset_index(drop=True, inplace=True)
                    count_series_merge = pd.merge(count_series_tc, df_priority_subset, how='inner', on=['cluster'])

                    del df_cluster_merge, df_cluster_pattern, df_priority, df_priority_subset, count_series_tc

                    # Splitting dataframes based on cluster IDs
                    df_cluster_0 = count_series_merge.loc[(count_series_merge["cluster"] == 0)]
                    df_cluster_1 = count_series_merge.loc[(count_series_merge["cluster"] == 1)]
                    df_cluster_2 = count_series_merge.loc[(count_series_merge["cluster"] == 2)]

                    # Sorting each element within each cluster based on the score
                    df_cluster_0 = df_cluster_0.sort_values(by=['Weighed_Score'], ascending=False)
                    df_cluster_1 = df_cluster_1.sort_values(by=['Weighed_Score'], ascending=False)
                    df_cluster_2 = df_cluster_2.sort_values(by=['Weighed_Score'], ascending=False)

                    # Ranking each element within a cluster
                    df_cluster_0['Recommended_Priority_based_Rank'] = np.arange(1, len(df_cluster_0) + 1)
                    df_cluster_1['Recommended_Priority_based_Rank'] = np.arange(1, len(df_cluster_1) + 1)
                    df_cluster_2['Recommended_Priority_based_Rank'] = np.arange(1, len(df_cluster_2) + 1)

                    # Concatenate all dataframes of all clusters
                    frame_combined = pd.concat([df_cluster_0, df_cluster_1, df_cluster_2], ignore_index=False)

                    del count_series_merge, df_cluster_0, df_cluster_1, df_cluster_2

                    frame_combined['Tester_assigned_priority'] = frame_combined.apply(lambda x: "High" if x[req_weight] == 1 else "Medium" if x[req_weight] == 2 else "Low", axis=1)

                    # Prioritized test cases with ranking
                    df_results = frame_combined[
                        [req_weight, sprint, 'Pass_percent', defect_sev, complexity, time, defects_count, test_case,
                         'Tester_assigned_priority', 'Recommended_Priority', 'Recommended_Priority_based_Rank']]

                    return df_results

                else:
                    raise RecordsEmptyError
            else:
                raise ColumnDoesNotExistError

        except FileFormatError:
            return {"error encountered": "the given is not xlsx or csv or xls"}

        except RecordsEmptyError:
            return {"error encountered": "Test case records are not available"}
        except ColumnDoesNotExistError:
            return {"error encountered": "Required columns doesn't exist"}
        except Exception as e:
            e = str(e)
            return {"error encountered": e}


# Flask operation starts here
app = Flask(__name__)


@app.route('/api/testpriority', methods=["POST"])
def testcasepriority():
    try:
        file = request.files['file']
        req_weight = request.form["req_weight"]
        sprint = request.form["sprint"]
        execution_status = request.form["execution_status"]
        defect_sev = request.form["defect_sev"]
        complexity = request.form["complexity"]
        time = request.form["time"]
        defects_count = request.form["defects_count"]
        test_case = request.form["test_case"]
        file.save(secure_filename(file.filename))
        df_results = TestCasePriority(file, req_weight, sprint, execution_status, defect_sev, complexity, time,
                                      defects_count, test_case)
        # Process 1
        df_final_clusters = df_results.priority_clusters()
        if isinstance(df_final_clusters, dict):
            # df_exception = json.dumps(df_final_clusters, indent=4)
            return df_final_clusters
        else:
            return df_final_clusters.to_json(indent=4, orient='records')
    except Exception as e:
        e = str(e)
        return {"error encountered": e}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
