#  coadsd_create_buffers_agol.py
#  this is a sample of how to create buffers from an existing feature service on arc gis online
#  this was taken from the ESRI samples and modified to use in the providecreated by John Clary for the Austin Code Department, Nov 2015
#  thanks to John Schulz, Austin Water

import urllib
import urllib2
import httplib
import time
import json
import contextlib

def submit_request(request):
    """ Returns the response from an HTTP request in json format."""
    with contextlib.closing(urllib2.urlopen(request)) as response:
        job_info = json.load(response)
        return job_info

def get_token(portal_url, username, password):
    """ Returns an authentication token for use in ArcGIS Online."""

    # Set the username and password parameters before
    #  getting the token. 
    #
    params = {"username": username,
              "password": password,
              "referer": "http://www.arcgis.com",
              "f": "json"}

    token_url = "{}/generateToken".format(portal_url)
    request = urllib2.Request(token_url, urllib.urlencode(params))
    token_response = submit_request(request)
    if "token" in token_response:
        print("Getting token...")
        token = token_response.get("token")
        return token
    else:
        # Request for token must be made through HTTPS.
        #
        if "error" in token_response:
            error_mess = token_response.get("error", {}).get("message")
            if "This request needs to be made over https." in error_mess:
                token_url = token_url.replace("http://", "https://")
                token = get_token(token_url, username, password)
                return token
            else:
                raise Exception("Portal error: {} ".format(error_mess))
            
def get_analysis_url(portal_url, token):
    """ Returns Analysis URL from AGOL for running analysis services."""

    print("Getting Analysis URL...")
    portals_self_url = "{}/portals/self?f=json&token={}".format(portal_url, token)
    request = urllib2.Request(portals_self_url)
    portal_response = submit_request(request)

    # Parse the dictionary from the json data response to get Analysis URL.
    #
    if "helperServices" in portal_response:
        helper_services = portal_response.get("helperServices")
        if "analysis" in helper_services:
            analysis_service = helper_services.get("analysis")
            if "url" in analysis_service:
                analysis_url = analysis_service.get("url")
                return analysis_url
    else:
        raise Exception("Unable to obtain Analysis URL.")

def analysis_job(analysis_url, task, token, params):
    """ Submits an Analysis job and returns the job URL for monitoring the job
        status in addition to the json response data for the submitted job."""
    
    # Unpack the Analysis job parameters as a dictionary and add token and
    # formatting parameters to the dictionary. The dictionary is used in the
    # HTTP POST request. Headers are also added as a dictionary to be included
    # with the POST.
    #
    print("Submitting analysis job...")
    
    params["f"] = "json"
    params["token"] = token
    headers = {"Referer":"http://www.arcgis.com"}
    task_url = "{}/{}".format(analysis_url, task)
    submit_url = "{}/submitJob?".format(task_url)
    request = urllib2.Request(submit_url, urllib.urlencode(params), headers)
    analysis_response = submit_request(request)
    if analysis_response:
        # Print the response from submitting the Analysis job.
        #
        print(analysis_response)
        return task_url, analysis_response
    else:
        raise Exception("Unable to submit analysis job.")

def analysis_job_status(task_url, job_info, token):
    """ Tracks the status of the submitted Analysis job."""

    if "jobId" in job_info:
        # Get the id of the Analysis job to track the status.
        #
        job_id = job_info.get("jobId")
        job_url = "{}/jobs/{}?f=json&token={}".format(task_url, job_id, token)
        request = urllib2.Request(job_url)
        job_response = submit_request(request)

        # Query and report the Analysis job status.
        #
        if "jobStatus" in job_response:
            while not job_response.get("jobStatus") == "esriJobSucceeded":
                time.sleep(5)
                request = urllib2.Request(job_url)
                job_response = submit_request(request)
                print(job_response)

                if job_response.get("jobStatus") == "esriJobFailed":
                    raise Exception("Job failed.")
                elif job_response.get("jobStatus") == "esriJobCancelled":
                    raise Exception("Job cancelled.")
                elif job_response.get("jobStatus") == "esriJobTimedOut":
                    raise Exception("Job timed out.")
                
            if "results" in job_response:
                return job_response
        else:
            raise Exception("No job results.")
    else:
        raise Exception("No job url.")

def analysis_job_results(task_url, job_info, token):
    """ Use the job result json to get information about the feature service
        created from the Analysis job."""

    # Get the paramUrl to get information about the Analysis job results.
    #
    if "jobId" in job_info:
        job_id = job_info.get("jobId")
        if "results" in job_info:
            results = job_info.get("results")
            result_values = {}
            for key in results.keys():
                param_value = results[key]
                if "paramUrl" in param_value:
                    param_url = param_value.get("paramUrl")
                    result_url = "{}/jobs/{}/{}?token={}&f=json".format(task_url, 
                                                                        job_id, 
                                                                        param_url, 
                                                                        token)
                    request = urllib2.Request(result_url)
                    param_result = submit_request(request)
                    job_value = param_result.get("value")
                    result_values[key] = job_value
            return result_values
        else:
            raise Exception("Unable to get analysis job results.")
    else:
        raise Exception("Unable to get analysis job results.")


if __name__ == '__main__':
        httplib.HTTPConnection._http_vsn = 10
        httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'

        username = "Change this to be your AGOL username"
        password = "Change this to be your AGOL password"
        host_url = "http://www.arcgis.com"
        portal_url = "{}/sharing/rest".format(host_url)
        token = get_token(portal_url, username, password)
        analysis_url = get_analysis_url(portal_url, token)
        feature_service = "http://services.arcgis.com/0L95CJ0VTaxqcmED/ArcGIS/rest/services/PLANNINGCADASTRE_overlay_capitol_dominance/FeatureServer/0"
        task = "CreateBuffers"
        output_service = "CreateBuffers_200"
        params = {"inputLayer": {"url":feature_service},
                  "distances": [20.0],
                  "units": "Feet",
                  "dissolveType": "None",
                  "outputName": {"serviceProperties":{"name": output_service}}}

        task_url, job_info = analysis_job(analysis_url, task, token, params)
        job_info = analysis_job_status(task_url, job_info, token)
        job_values = analysis_job_results(task_url, job_info, token)
