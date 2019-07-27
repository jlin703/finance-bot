from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from googleapiclient.errors import HttpError
import argparse
import json
import numpy as np

def get_arg_parser(description=None):
    '''Returns an argparser object, that inherits from tools.argparser.

    Use this to get an arg parser that does not conflict with the Oauth2 procedure.'''
    if description:
        parser = argparse.ArgumentParser(description, parents=[tools.argparser])
    else:
        parser = argparse.ArgumentParser(parents=[tools.argparser])
    return parser


def get_google_service(SCOPES, token_name, api_type='drive', version='v3',
                       creds_file='credentials.json', flags=None):
    '''
    This function returns the service object with the given SCOPES and token name.

    SCOPES      This parameter is used to determine how much power the app can have.
                Examples of this are 'https://www.googleapis.com/auth/drive'
                See here for all the available options.
                https://developers.google.com/drive/api/v3/about-auth
    token_name  To cache the authentication procedure, the Google API will want to create a token file,
                which you will present to the server when you want to perform some action. The tokens
                will end up being stored in token_name + '.json'
    api_type    The type of API that you want (e.g. 'drive' or 'sheets')
    version     The version number (e.g. 'v3')
    creds_file  This file is where your credentials are stored. Make sure to get one from the Google API
                console!
    flags       A Namespace object that is the command line arguments. You can pass this in after
                calling ArgumentParser.parse_args(). The result of that you may pass in as flags.
                Otherwise, this function will call parse_args().

    Returns:
        A service object that can be used to perform actions.
    '''
    # The file perfile_token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    store = file.Storage(token_name + '.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(creds_file, SCOPES)
        creds = tools.run_flow(flow, store, flags=flags)
    service = build(api_type, version, http=creds.authorize(Http()))
    return service

def load_json_file(filename):
    '''
    Takes a JSON file and returns a Python object representation of that JSON object.
    '''
    with open(filename, 'r') as f:
        return json.load(f)

def store_json_file(obj, filename):
    '''Takes an object and stores it as a JSON file.'''
    with open(filename, 'w') as f:
        json.dump(obj, f, indent=4, sort_keys=False)

def id_to_name(id_str, service):
    '''Retrives the name of the id

    id_str      A string that is the ID of the file in which we wish to get the name of.
    service     A Google API service object that will let us get the name.

    Returns: the filename of the file on Google Drive with the FileId id_str'''
    return service.files().get(fileId=id_str, fields="name").execute().get('name', '')


def get_column_names_of_sheet(spreadId, sheetName, service):
    '''Retrives a list of columns from the spreadsheet'''
    resp = service.spreadsheets().values().get(spreadsheetId=spreadId, range="'%s'" % sheetName).execute()
    return resp['values'][0]

def pathname_to_id(pathname, service):
    '''Finds the FileID with a pathname. For example "CS 70 Fall 2018/Spreadsheet".

    NOTE: please make sure that all your folders are uniquely named. Otherwise, this will
    just pick an arbitrary route to traverse down.

    pathname        A string that uses slashes to denote directory structure.
    service         A Google API service object that has permissions to read all of Google Drive.

    Returns: A string that is the ID of the file/folder, or None, if this does not exist.
    '''
    folders = pathname.split('/')
    folders = [item for item in folders if item] # Throw out empty strings in case of a/b//c

    parent_id = None
    for i, folder in enumerate(folders):
        query = "name='%s' and not trashed" % folder
        if parent_id:
            query += " and '%s' in parents" % parent_id
        resp = service.files().list(q=query, fields="files(id)").execute()
        files = resp.get("files", [])
        if not files:
            return None
        if len(files) > 1:
            print("Warning: multiple occurrences of", "/".join(folders[:i+1]))
            print("Picking the first one found")
        parent_id = files[0]['id']

    return parent_id

def write_to_spreadsheet(spreadsheetId, cells, values, service, valueInputOption='USER_ENTERED'):
    '''
    Writes data to a spreadsheet.

    spreadsheetId       The ID of the spreadsheet that you want to update
    cells               The cells you want to update in A1 notation
    values              The 2D list of things you want to put into the cells
    service             The google service that you are using.
    valueInputOption    Either 'USER_ENTERED' or 'RAW'
    '''

    body = {'values': values}
    service.spreadsheets().values().update(spreadsheetId=spreadsheetId, valueInputOption=valueInputOption,
                                           body=body, range=cells).execute()

def batch_read_from_spreadsheet(spreadsheetId, ranges, service, majorDimension='ROWS'):
    resp = service.spreadsheets().values().batchGet(spreadsheetId=spreadsheetId,
                                                    ranges=ranges, majorDimension=majorDimension
                                                    ).execute()
    return [r['values'] for r in resp['valueRanges']]

def read_from_spreadsheet(spreadsheetId, cells, service, majorDimension='ROWS'):
    '''
    Reads data from a spreadsheet.
    '''
    resp = service.spreadsheets().values().get(spreadsheetId=spreadsheetId,
                                               range=cells, fields='values',
                                               majorDimension=majorDimension).execute()
    return resp['values']

def get_colors_from_spreadsheet(spreadsheetId, cells, service):
    '''
    Gets colors from the spreadsheet.

    spreadsheetId       The ID of the spreadsheet you want colors from
    cells               The cells that you want in A1 notation, e.g. 'Section Sign-up'!G9:X31
    service             The Google API service object that you got from running get_google_service
    '''
    fields = "sheets(data.rowData(values.effectiveFormat.backgroundColor))"
    resp = service.spreadsheets().get(spreadsheetId=spreadsheetId,
                                            ranges=cells,
                                            includeGridData=True,
                                            fields=fields).execute()

    arr = resp['sheets'][0]['data'][0]['rowData']

    ret = np.zeros((len(arr), len(arr[0]['values']), 3)) # RGB values
    for i in range(len(arr)):
        vals = arr[i]['values']
        for j in range(len(vals)):
            # Interpret empty format as white cell
            bg_color = vals[j].get('effectiveFormat', {'backgroundColor': {'red': 1, 'green': 1, 'blue': 1}})
            ret[i][j][0] = bg_color['backgroundColor'].get('red', 0)
            ret[i][j][1] = bg_color['backgroundColor'].get('green', 0)
            ret[i][j][2] = bg_color['backgroundColor'].get('blue', 0)

    return ret


def num_to_alpha(num):
    '''zero indexed'''
    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return ALPHABET[num]

