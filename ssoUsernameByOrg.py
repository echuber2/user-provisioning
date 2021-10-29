#! /usr/bin/env python3
#
# Pre-reqs:
#    pip3 install -r requirements.txt
#
# Usage: python3 ssoUsernameByOrg github-organization-name
#
# Returns CSV of    GithubUsername,netid@illinois.edu
#
# Set GITHUB_TOKEN environment variable (or .env file) to your personal access token
#

import requests
import json
import argparse
import os

from pprint import pprint
from dotenv import load_dotenv

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('org')
args = arg_parser.parse_args()

load_dotenv()
token = os.getenv('GITHUB_TOKEN')
if not token:
    raise Exception('missing GITHUB_TOKEN env var (put in .env)')

# Unused
# from github import Github
# g = Github(token)

def get_json_from_response(r):
    try:
        status = r.status_code
        reason = None
        message = None
        errors = None
        json_fail = False
        try:
            reason = r.reason
        except:
            reason = None
        reason = reason or '(No reason given)'
        try:
            r_json = r.json()
        except:
            message = "(Can't decode json)"
            r_json = None
            json_fail = True
        if r_json:
            try:
                message = r_json['message']
            except:
                message = None
            try:
                errors = r_json['errors']
            except:
                errors = None
        message = message or '(No message given)'
        if status != 200 or json_fail:
            if status in [404, 405]:
                reason += ' (GitHub API URL might be wrong)'
            if status == 401:
                reason += ' (Check token)'
            raise Exception(f'Error. [Status: {status}] [Reason: {reason}] [Message: {message}]')
        if errors is not None:
            raise Exception(f'Errors: {errors}')
        return r_json
    except AttributeError:
        raise Exception('Expected Response object')

# Please note that the 'first: 100' part should remain hard-coded
# and should not be changed or parameterized. This script pulls
# 100 results at a time (the most allowed) and cycles until it
# retrieves everything possible.
query = """
query($organization: String!, $endCursor: String) {
  organization(login: $organization) {
    samlIdentityProvider {
      ssoUrl,
      externalIdentities(first: 100, after: $endCursor) {
        edges {
          node {
            guid,
            samlIdentity {
              nameId
            }
            user {
              login
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}"""

variables = {
    'organization': args.org,
    'endCursor': None,
}

headers = {
    'authorization': 'bearer ' + token,
    'content-type': 'application/json',
    'accept-encoding': 'gzip',
}

hasNextPage = True
while hasNextPage:
    r = requests.post('https://api.github.com/graphql',
        json={'query': query, 'variables': variables}, headers=headers)
    out_j = get_json_from_response(r)
    # pprint(out_j)
    try:
        externalIdentities = out_j["data"]["organization"]["samlIdentityProvider"]["externalIdentities"]
        for node in externalIdentities["edges"]:
            username = node["node"]["user"]["login"]
            samlId = node["node"]["samlIdentity"]["nameId"]
            print("{},{}".format(username, samlId))
    except KeyError as e:
        raise Exception(f"GraphQL response did not contain expected key: {e}")
    try:
        variables["endCursor"] = externalIdentities['pageInfo']['endCursor']
    except KeyError:
        variables["endCursor"] = None
    try:
        hasNextPage = externalIdentities['pageInfo']['hasNextPage']
    except KeyError:
        hasNextPage = False
