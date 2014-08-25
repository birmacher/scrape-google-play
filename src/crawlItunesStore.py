'''
Created on Sep 7, 2013

@author: anuvrat
'''
import pickle
from datetime import datetime
import urllib2
from bs4 import BeautifulSoup
import re
import string
import json
import codecs
import pdb
import sys

def loadState():
    try:
        state_file = open( "itunes_store_state_dump.pba", "rb" )
        apps_discovered = pickle.load( state_file )
        apps_pending = pickle.load( state_file )
        state_file.close()
        print( "Pending = ", len( apps_pending ), " Discovered = ", len( apps_discovered ) )
        return apps_discovered, apps_pending
    except IOError:
        print( "A fresh start ..." )
        return [], []

character_encoding = 'utf-8'
apps_discovered, apps_pending = loadState()
count_offset = len( apps_discovered )
apps_categories = {}

start_time = datetime.now()

def getPage( url ):
    try:
        #print "Loading url " + url
        response = urllib2.urlopen( url )
    except urllib2.HTTPError as e:
        print( "HTTPError with: ", url, e )
        return None
    the_page = response.read()
    return the_page

def getPageAsSoup( url ):
    the_page = getPage( url )
    soup = BeautifulSoup( the_page )
    return soup

def getJSON( url ):
    the_page = getPage( url )
    #print(the_page)
    decoded_data = json.loads( the_page.decode('utf-8') )
    return decoded_data

def reportProgress():
    current_time = datetime.now()
    elapsed = current_time - start_time
    v = ( ( len( apps_discovered ) - count_offset ) / elapsed.seconds ) * 60 if elapsed.seconds > 0 else 0
    t = len( apps_pending ) / v if v > 0 else 0
    print( "Pending = ", len( apps_pending ), " Discovered = ", len( apps_discovered ), " Velocity = ", str( v ), " parsed per min and Time remaining in min = ", str( t ) )
    print( json.dumps( apps_categories ) )

def saveState():
    state_file = open( "itunes_store_state_dump.pba", "wb" )
    pickle.dump( apps_discovered, state_file )
    pickle.dump( apps_pending, state_file )
    state_file.close()
    reportProgress()

def getApps( categoryUrl ):
    previous_apps = []
    start_idx = 1
    while( True ):
        url = categoryUrl + "&page=" + str( start_idx )
        print( url )
        categoryPage = getPageAsSoup( url )
        allAppLinks = [aDiv.get( 'href' ) for aDiv in categoryPage.findAll( 'a', href = re.compile( '^https://itunes.apple.com/us/app' ) )]
        if allAppLinks == previous_apps: break
        apps_pending.extend( [appLink for appLink in allAppLinks if appLink not in apps_pending] )
        writeAppDetails( apps_pending )
        previous_apps = allAppLinks
        start_idx += 1
    saveState()

def getAppDetails( appUrl ):
    if appUrl in apps_discovered: return None

    # e.g. appUrl: https://itunes.apple.com/us/app/calorie-counter-diet-tracker/id341232718?mt=8

    matches = re.search("/id([0-9]+)\?", appUrl)
    appid = matches.groups()[0]
    #print (appid)
    appDetails = getJSON("https://itunes.apple.com/lookup?id=" + appid)
    apps_discovered.append( appUrl )

    return appDetails

def closeFileHandlers( fileHandlers ):
    for v in fileHandlers.values():
        v.close()

def writeAppDetails ( apps_pending ):
    fileHandlers = {}
    count = 100
    while apps_pending:
        if count == 0:
            saveState()
            count = 100
        count = count - 1

        app = apps_pending.pop()
        if not app: continue

        #print "Attepting to get app details for " + app
        try:
            app_data = getAppDetails( app )
        except Exception as e:
            print( app, e )
            exit( 1 )

        if not app_data:
            continue

        category = None
        try:
            app_results = app_data['results'][0]
            category = app_results['genres'][0]
        except Exception as e:
            print ( app, e, app_data )

        if not category: category = 'uncategorized'

        if category.lower() not in fileHandlers:
            fileHandlers[category.lower()] = codecs.open( '/'.join( ["apple_appstore", category.lower()] ), 'ab', character_encoding, buffering = 0 )
            apps_categories[category.lower()] = 0
        apps_categories[category.lower()] = apps_categories[category.lower()] + 1
        fileHandler = fileHandlers[category.lower()]
        try:
            fileHandler.write( json.dumps( app_data ) + "\n \n" )
        except Exception as e:
            print( app, e )

    saveState()
    closeFileHandlers( fileHandlers )


if __name__ == '__main__':
    itunesStoreUrl = 'https://itunes.apple.com/us/genre/ios/id36?mt=8'
    mainPage = getPageAsSoup( itunesStoreUrl )
    allCategories = []
    for column in ['list column first', 'list column', 'list column last']:
        columnDiv = mainPage.find( 'ul', {'class' : column} )
        allCategories.extend( aDiv.get( 'href' ) for aDiv in columnDiv.findAll( 'a', href = re.compile( '^https://itunes.apple.com/us/genre' ) ) )

    for category, alphabet in [( x, y ) for x in allCategories for y in string.ascii_uppercase]:
        getApps( category + '&letter=' + alphabet )


