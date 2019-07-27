from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import argparse

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

def get_column_names_of_sheet(spreadId, sheetName, service):
    '''Retrives a list of columns from the spreadsheet'''
    resp = service.spreadsheets().values().get(spreadsheetId=spreadId, range="'%s'" % sheetName).execute()
    return resp['values'][0]

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
