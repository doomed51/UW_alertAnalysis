from datetime import datetime
from os import P_DETACH, replace
from matplotlib.colors import LinearSegmentedColormap
from numpy.core.defchararray import index
from numpy.core.fromnumeric import partition
from numpy.lib.npyio import load
from numpy.testing._private.nosetester import run_module_suite
from openpyxl import workbook, load_workbook
from openpyxl.worksheet import worksheet
from sklearn.cluster import KMeans

import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
import time

# Input: symbol name or sheet name 
# Out: Dataframe of cleansed alerts  
# Why: less effort to go between symbol alert and general alert spreadsheet
def getAlerts(symbolOrSheetName):
    # Location of the file that contains the alerts dump
    filePaths = [r"F:\workbench\UW_Alerts\UW_alerts_symbols.xlsx", 
        r"F:\workbench\UW_Alerts\UW_alerts.xlsx",
        r"F:\workbench\UW_Alerts\UW_alerts_myHunt.xlsx"]
    print('')
    print('#########################################################')
    print('Loading files ...')
    start = time.perf_counter()
    
    workbook_symbol = load_workbook(filename=filePaths[0])
    workbook = load_workbook(filename=filePaths[1])
    workbook_myHunt = load_workbook(filename=filePaths[2])

    print('Success!')
    print('')
    if symbolOrSheetName in workbook_symbol.sheetnames:
        print('Sheet found, loading alerts ...')
        alertsDF_map = pd.read_excel(filePaths[0], sheet_name=None)
    elif symbolOrSheetName in workbook.sheetnames:
        print('Sheet found, loading alerts ...')
        alertsDF_map = pd.read_excel(filePaths[1], sheet_name=None)
    elif symbolOrSheetName in workbook_myHunt.sheetnames:
        print('Sheet found, loading alerts ...')
        alertsDF_map = pd.read_excel(filePaths[2], sheet_name=None)
    else:
        print("Sheet not found!!")
        exit()
    
    end = time.perf_counter()
    print('Success!')
    print('')
    print(f"Elapsed Time: {end - start:0.4f} seconds")
    print('#########################################################')
    print('')

    return cleanAlertsData(alertsDF_map[symbolOrSheetName])
    

    

#####
# Util function
##
# replace 'C' and 'P' with 'Call' and 'Put'
#####
def replaceText(row):
    strike = row['Strike'][-1]
    if strike == 'C':
        return 'Call'
    else:
        return 'Put'
#####
# Util function
##
# Remove the trailing char in a string 
#####
def cleanStrike(row):
    return row['Strike'][:-1]

#####
# Cleans up the alerts extract - NaNs etc. 
# splits up option chain column into symbol, strike and option type
# Splits up Max gain and loss columns into % and abs. 
#####
def cleanAlertsData(alertsDF):
    # drop: Action, Emojis columns
    alertsDF = alertsDF.drop(columns=['Actions'], axis=1) 

    # clean up Time column i.e. alert time, leaving only the date
    
    print(alertsDF['Time'].max())
    print("")
    print(alertsDF['Time'].head(10))
    print("")
    print("")

    alertsDF['Alert Date'] = alertsDF['Time'].astype(str).str[:-9]
    alertsDF['Alert Date'] = pd.to_datetime(alertsDF['Alert Date'], dayfirst=True)
    alertsDF['Expiry'] = pd.to_datetime(alertsDF['Expiry'], dayfirst=True)

    print(alertsDF['Alert Date'].max())
    print("")
    print(alertsDF['Alert Date'].head(10))


    # remove trailing spaces & recast 
    alertsDF['Option'].str.strip()
    alertsDF['Option'] = alertsDF['Option'].astype('str')
    alertsDF['Option'] = alertsDF['Option'].str.strip()

    #split the Option col into symbol and strike
    alertsDF[['Option', 'Strike']] = alertsDF['Option'].str.split('$', expand=True)
    alertsDF['Strike'] = alertsDF['Strike'].str.strip()
    alertsDF.rename(columns={'Option': 'Symbol'}, inplace=True)

    #format the new option type & strike columns
    alertsDF['Option Type'] = alertsDF.apply(replaceText, axis = 1)
    alertsDF['Strike'] = alertsDF.apply(cleanStrike, axis=1)
    alertsDF['Strike'] = alertsDF['Strike'].str.replace(',', '')
    alertsDF['Strike'] = alertsDF['Strike'].astype('float')

    # Clean up Max Gain columns
    # split into individual $ and % columns
    # recast columns to ensure they are floats 
    # drop the old columns 
    alertsDF[['Max Gain', 'Max Gain %']] = alertsDF['High'].str.split(' ', expand=True)
    alertsDF['Max Gain'] = alertsDF['Max Gain'].str.replace('$', '', regex=True)
    alertsDF['Max Gain'] = alertsDF['Max Gain'].str.replace(',', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace(')', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace('(', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace('%', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace(',', '', regex=True)
    alertsDF['Max Gain'] = alertsDF['Max Gain'].astype('float')
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].astype('float')

    # Clean up Max Loss columns
    # split into individual $ and % columns
    # recast columns to ensure they are floats
    alertsDF[['Max Loss', 'Max Loss %']] = alertsDF['Low'].str.split(' ', expand=True)
    alertsDF['Max Loss'] = alertsDF['Max Loss'].str.replace('$', '', regex=True)
    alertsDF['Max Loss'] = alertsDF['Max Loss'].str.replace(',', '', regex=True)
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace(')', '', regex=True)
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace('(', '', regex=True)
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace('%', '', regex=True)
    #alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace(',', '', regex=True)
    alertsDF['Max Loss'] = alertsDF['Max Loss'].astype('float')
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].astype('float')

    # making sure no NaN's 
    alertsDF.fillna(0, inplace=True)

    # drop the old columns
    alertsDF = alertsDF.drop(columns=['High','Low', 'Time'], axis=1)

    #####
    # Adding compuited columns:
    # 'DTE' Date to Expiry of the option when the alert was first fired 
    alertsDF['DTE'] = (alertsDF['Expiry'] - alertsDF['Alert Date']).dt.days

    return alertsDF

#####
# Create slices of alertsDF data based on the % return
# for easier analysis 
#####
# TODO deprecate this function....
# 
# TODO make this function actually return a dataframe
# TODO add .copy() to df selection
# TODO append the slices into 1 data frame 
# TODO have to escape empty dataframe results on the .loc
def createSlices_maxGain(alertsDF):
    maxGainSlices = pd.DataFrame()
    
    below0 = alertsDF.loc[alertsDF['Max Gain %'] <= 0].copy()
    below0['Slice'] = 'below50'
    
    below50 = alertsDF.loc[(alertsDF['Max Gain %'] <= 50) & (alertsDF['Max Gain %'] > 0)].copy()
    below50['Slice'] = 'below50'
    maxGainSlices.append(below0, below50)
    below100 = alertsDF.loc[(alertsDF['Max Gain %'] <= 100) & (alertsDF['Max Gain %'] > 50)]
    over100 = alertsDF.loc[(alertsDF['Max Gain %'] <= 200) & (alertsDF['Max Gain %'] > 100)]
    over200 = alertsDF.loc[(alertsDF['Max Gain %'] <= 1000) & (alertsDF['Max Gain %'] > 200)]
    over1000 = alertsDF.loc[(alertsDF['Max Gain %'] > 1000)]

#####
# Plot Max Gain % as the following: 
# 1. Call/Put highs over time 
# 2. highs histogram (call/put combined) 
#####
def plotReturns(alertsDF, title="Calls vs. Puts"): 
    #fig, ax = plt.subplots(2)
    #ax[0].plot(alertsDF['Alert Date'], alertsDF['Max Gain %'], #label='Option Type')
    #ax[1] = alertsDF['Max Gain %'].plot.hist(bins = bins, alpha=1)
    
    #alertsDF.plot(kind='line', x='Alert Date', y='Max Gain %', color=alertsDF['Option Type'] )
    alertsDF.sort_values(by='Alert Date', inplace=True, ascending=False)
    calls = alertsDF.loc[alertsDF['Option Type'] == 'Call']
    puts = alertsDF.loc[alertsDF['Option Type'] == 'Put']

    plt.plot( calls['Alert Date'], calls['Max Gain %'], color = 'g',label='Calls' )

    plt.plot( puts['Alert Date'], puts['Max Gain %'], color = 'r', label='Puts' )
    plt.title(label=title)
    plt.legend()
    plt.show()

#####
# Cleaninig up the slices to remove unnneeded columns i.e. strings 
# to prepare for KMeans analysis 
#####
def prepAlertsDataForKMeans(alertsDF, type='all'):

    dataframeOfFloats = pd.DataFrame()

    if type == 'all':
        dataframeOfFloats = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Sector', 'Underlying', '% Diff', 'Ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )
    

    elif type == 'optionType':
        dataframeOfFloats = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Sector', 'Underlying', 'Ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

    elif type == 'sector':
        dataframeOfFloats = alertsDF.drop(['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Underlying', '% Diff', 'Ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

    return dataframeOfFloats

#####
# clustering - elbow method 
##
# Results: 
# All alerts -> 2 - 4
# over200 -> 2 - 5
#####
def elbowMethod(dataframeOfFloats):
    clusters = []

    for i in range(1, 11):
        km = KMeans(n_clusters=i).fit(dataframeOfFloats)
        clusters.append(km.inertia_)

    fig, ax = plt.subplots(figsize=(12,8))
    sns.lineplot(x=list(range(1,11)), y=clusters, ax=ax)
    ax.set_title('Searching for Elbow')
    ax.set_xlabel('Clusters')
    ax.set_ylabel('Intertia')

    plt.show()

#####
# Clustering & plotting
#####
def plotCluster(myDF, numClusters):
    km3 = KMeans(n_clusters = numClusters).fit(myDF)
    myDF['Labels'] = km3.labels_ 
    
    plt.figure(figsize=(12, 8))
    sns.scatterplot(myDF['Volume'], myDF['Max Gain %'], hue=myDF['Labels'],
    palette=sns.color_palette('hls', numClusters))
    plt.title('KMeans with 2 clusters')
    print(myDF.head())
    
    plt.show()

#####
# Returns a df with stats for the passed in alerts dataframe
# Alert dataset contains multiple or a single symbol
#####
def generalAlertStats(alertsDF1, sliceName = 'default', sheetName = 'default'):
    totalAlerts = alertsDF1['Expiry'].count()
    totalPostiveAlerts = alertsDF1.loc[alertsDF1['Max Gain %'] > 0]['Alert Date'].count()
    totalNegativeAlerts = alertsDF1.loc[alertsDF1['Max Gain %'] <= 0]['Alert Date'].count()

    # if the # of unique symbols > 1
    colName = ''
    if alertsDF1['Symbol'].nunique() == 1:
        colName = 'Symbol'
        colVal = alertsDF1.iloc[0]['Symbol']
    else:
        colName = 'Sheet Name'
        colVal = sheetName

    percentStatsData = {
        #'Symbol': [alertsDF['Symbol']],
        colName: [ colVal ],
        
        'Slice Name': [sliceName],
        
        'Period Start': [alertsDF1['Alert Date'].min().strftime('%Y-%m-%d')], 
        
        'Period End': [alertsDF1['Alert Date'].max().strftime('%Y-%m-%d')],
        
        'Total Alerts': [alertsDF1['Alert Date'].count()], 
        
        'Percent Positive': [totalPostiveAlerts / totalAlerts * 100],

        'Percent Above 100': [alertsDF1.loc[(alertsDF1['Max Gain %'] >= 100)]['Alert Date'].count() / totalAlerts * 100],
        
        'Percent Negative': [totalNegativeAlerts / totalAlerts * 100],
        
        'Gain % (Calls)': [alertsDF1.loc[alertsDF1['Option Type'] == 'Call']['Max Gain %'].mean()],
        
        'Gain % (Puts)': [alertsDF1.loc[alertsDF1['Option Type'] == 'Put']['Max Gain %'].mean()],
        
        '<0' : [alertsDF1.loc[(alertsDF1['Max Gain %'] <= 0)]['Alert Date'].count() / totalAlerts * 100],
        
        '0-20': [alertsDF1.loc[(alertsDF1['Max Gain %'] <= 20) & (alertsDF1['Max Gain %'] > 0)]['Alert Date'].count() / totalAlerts * 100],
        
        '21-50': [alertsDF1.loc[(alertsDF1['Max Gain %'] <= 50) & (alertsDF1['Max Gain %'] > 20)]['Alert Date'].count() / totalAlerts * 100],
        
        '51-100': [alertsDF1.loc[(alertsDF1['Max Gain %'] <= 100) & (alertsDF1['Max Gain %'] > 50)]['Alert Date'].count() / totalAlerts * 100],
        
        '101-200': [alertsDF1.loc[(alertsDF1['Max Gain %'] <= 200) & (alertsDF1['Max Gain %'] > 100)]['Alert Date'].count() / totalAlerts * 100],
        
        '201-500': [alertsDF1.loc[(alertsDF1['Max Gain %'] <= 500) & (alertsDF1['Max Gain %'] > 200)]['Alert Date'].count() / totalAlerts * 100],
        
        '500+': [alertsDF1.loc[(alertsDF1['Max Gain %'] > 500)]['Alert Date'].count() / totalAlerts * 100]

    }
    percentStats = pd.DataFrame(percentStatsData)
    percentStats = percentStats.round(2)
    return percentStats

#####
# Generates a dataframe that contains performance statistics 
# of different slices of the passed in alerts dataframe
##
# new DF = [ Symbol, Slice, stats pulled from generalAlertStat():::]
# if sheetName = default i.e. no sheetName is passed, the code assumes
# that the passed in alerts are for a single symbol
#####
def generateSliceStats(alertsDF, sheetName = 'default'):
    
    alertSlices = generalAlertStats(alertsDF, 'baseline', sheetName=sheetName)
    
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Total $'] < 100000) & (alertsDF['OI'] < alertsDF['Volume']))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'$vol<100K;OI<Vol', sheetName=sheetName ))

    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Total $'] < 100000) & (alertsDF['IV'] < 40))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'$vol<100K;IV<40', sheetName=sheetName ))
    
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['DTE'] > 20))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'DTE>20', sheetName=sheetName ))
    
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['DTE'] < 20))]
    if not alertsDF_reduced.empty:
         alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'DTE<20', sheetName=sheetName ))

    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Tier'] == 'premium') & (alertsDF['DTE'] > 20))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'Premium; DTE>20', sheetName=sheetName ))
    
    # ask < 4;  volume < median;    % diff > 20
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Ask'] < 4) & (alertsDF['Volume'] > alertsDF['Volume'].median()) & (alertsDF['% Diff'] > 0.2) )]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'ask<4;vol>med;diff>20', sheetName=sheetName ))
    
    # Calls that are tagged as Bullish 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Call') & (alertsDF['Emojis'].str.contains("Bullish") ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'CallsBullish', sheetName=sheetName ))

    # Calls that are tagged as Bullish + Ask side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Call') & (alertsDF['Emojis'].str.contains("Bullish") & (alertsDF['Emojis'].str.contains("Ask Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'CallsBullishAskSide', sheetName=sheetName ))

    # Calls that are tagged as Bullish + Bid side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Call') & (alertsDF['Emojis'].str.contains("Bullish") & (alertsDF['Emojis'].str.contains("Bid Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'CallsBullishBidSide', sheetName=sheetName ))

    # Calls that are tagged as Bearish + Ask side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Call') & (alertsDF['Emojis'].str.contains("Bearish") & (alertsDF['Emojis'].str.contains("Ask Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'CallsBearishAskSide', sheetName=sheetName ))

    # Calls that are tagged as Bearish + Bid side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Call') & (alertsDF['Emojis'].str.contains("Bearish") & (alertsDF['Emojis'].str.contains("Bid Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'CallsBearishBidSide', sheetName=sheetName ))
    
    # Puts that are tagged as Bullish + Ask side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Put') & (alertsDF['Emojis'].str.contains("Bullish") & (alertsDF['Emojis'].str.contains("Ask Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'PutsBullishAskSide', sheetName=sheetName ))

    # Puts that are tagged as Bullish + Bid side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Put') & (alertsDF['Emojis'].str.contains("Bullish") & (alertsDF['Emojis'].str.contains("Bid Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'PutsBullishBidSide', sheetName=sheetName ))

    # Puts that are tagged as Bearish  
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Put') & (alertsDF['Emojis'].str.contains("Bearish") ) )]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'PutsBearish', sheetName=sheetName ))

    # Puts that are tagged as Bearish + Ask side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Put') & (alertsDF['Emojis'].str.contains("Bearish") & (alertsDF['Emojis'].str.contains("Ask Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'PutsBearishAskSide', sheetName=sheetName ))

    # Puts that are tagged as Bearish + Bid side 
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Option Type'] == 'Put') & (alertsDF['Emojis'].str.contains("Bearish") & (alertsDF['Emojis'].str.contains("Bid Side")) ))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'PutsBearishBidSide', sheetName=sheetName ))

    # Alert age < 5 days
    alertsDF_reduced = alertsDF.loc[ ((datetime.today() - alertsDF['Alert Date']).dt.days < 5)]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'alert<5', sheetName=sheetName ))
    
    # Alert age > 5 days
    alertsDF_reduced = alertsDF.loc[ ((datetime.today() - alertsDF['Alert Date']).dt.days > 5)]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'alert>5', sheetName=sheetName ))
    
    # Alert age > 10 days
    alertsDF_reduced = alertsDF.loc[ ((datetime.today() - alertsDF['Alert Date']).dt.days > 10)]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'alert>10', sheetName=sheetName ))

    # alertsDF['DTE'] = (alertsDF['Expiry'] - alertsDF['Alert Date']).dt.days

    return alertSlices
#####
# Takes in any Alerts dump and returns the alerts that are within the passed in sliceName
#####
def getSliceAlerts(alertsDF, sliceName):
    
    selectedSlice = alertsDF
    
    if sliceName == '$vol<100K;OI<Vol':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Total $'] < 100000) & (selectedSlice['OI'] < selectedSlice['Volume']))]
    
    elif sliceName == 'DTE>20':
        selectedSlice = selectedSlice.loc[ ( selectedSlice['DTE'] > 20)]

    elif sliceName == 'DTE<20':
        selectedSlice = selectedSlice.loc[ ( selectedSlice['DTE'] < 20)]
        
    elif sliceName == 'Premium; DTE>20':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Tier'] == 'premium') & (selectedSlice['DTE'] > 20))]
    
    elif sliceName == 'Premium; DTE<20':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Tier'] == 'premium') & (selectedSlice['DTE'] < 20))]
        
    elif sliceName == 'ask<4;vol>med;diff>20':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Ask'] < 4) & (selectedSlice['Volume'] > selectedSlice['Volume'].median()) & (selectedSlice['% Diff'] > 0.2) )]
    
    elif sliceName == '$vol<100K;IV<40':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Total $'] < 100000) & (selectedSlice['IV'] < 40))]
    
    elif sliceName == 'CallsBullish':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Call') & (selectedSlice['Emojis'].str.contains("Bullish")) )]

    elif sliceName == 'CallsBullishAskSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Call') & (selectedSlice['Emojis'].str.contains("Bullish") & (selectedSlice['Emojis'].str.contains("Ask Side")) ))]

    elif sliceName == 'CallsBullisBidSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Call') & (selectedSlice['Emojis'].str.contains("Bullish") & (selectedSlice['Emojis'].str.contains("Bid Side")) ))]
    
    elif sliceName == 'CallsBearishBidSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Call') & (selectedSlice['Emojis'].str.contains("Bearish") & (selectedSlice['Emojis'].str.contains("Bid Side")) ))]
    
    elif sliceName == 'CallsBearishAskSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Call') & (selectedSlice['Emojis'].str.contains("Bearish") & (selectedSlice['Emojis'].str.contains("Ask Side")) ))]
        
    elif sliceName == 'PutsBullishAskSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Put') & (selectedSlice['Emojis'].str.contains("Bullish") & (selectedSlice['Emojis'].str.contains("Ask Side")) ))]
        
    elif sliceName == 'PutsBullishBidSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Put') & (selectedSlice['Emojis'].str.contains("Bullish") & (selectedSlice['Emojis'].str.contains("Bid Side")) ))]

    elif sliceName == 'PutsBearish':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Put') & (selectedSlice['Emojis'].str.contains("Bearish") ))]

    elif sliceName == 'PutsBearishBidSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Put') & (selectedSlice['Emojis'].str.contains("Bearish") & (selectedSlice['Emojis'].str.contains("Bid Side")) ))]
    
    elif sliceName == 'PutsBearishAskSide':
        selectedSlice = selectedSlice.loc[ ( (selectedSlice['Option Type'] == 'Put') & (selectedSlice['Emojis'].str.contains("Bearish") & (selectedSlice['Emojis'].str.contains("Ask Side")) ))]
    
    elif sliceName == 'alert<5days':
        selectedSlice = selectedSlice.loc[ ((datetime.today() - selectedSlice['Alert Date']).dt.days < 5)]

    elif sliceName == 'alert>5days':
        selectedSlice = selectedSlice.loc[ ((datetime.today() - selectedSlice['Alert Date']).dt.days > 5)]

    elif sliceName == 'alert>10days':
        selectedSlice = selectedSlice.loc[ ((datetime.today() - selectedSlice['Alert Date']).dt.days > 10)]

    return selectedSlice.sort_values(by='Max Gain %', ascending=False)

#####
# Returns a dataframe that allows for comparisons between
# alert stats of the passed in array of symbols
#####
def compareAlertSlices(sheetNames):
    alertsDF_combined = pd.DataFrame()
    
    for mySheetName in sheetNames:
        myAlerts = cleanAlertsData(alertsDF_map[mySheetName])
        
        if myAlerts['Symbol'].nunique() == 1:
            alertsDF_combined = alertsDF_combined.append(
            generateSliceStats(
            myAlerts), ignore_index=True
            )
        
        else:
            alertsDF_combined = alertsDF_combined.append(
            generateSliceStats(
            myAlerts, sheetName=mySheetName), ignore_index=True
            )
        
    return alertsDF_combined

#####
# Funtion to run computations on the entire body of available 
# symbols 
#####
def globalSymbolAnalysis():
    print('')
    print('#########################################################')
    print('Analyzing all available symbols')
    start = time.perf_counter()
    
    #symbolList = alertsDF_map.keys()
    globalAlertStats = compareAlertSlices(alertsDF_map.keys())
    globalAlertStats.sort_values(by='Percent Above 100', inplace=True, ascending=False)
    
    end = time.perf_counter()
    print('Success!!')
    print('')
    print(f"Elapsed Time: {end - start:0.4f} seconds")
    #print('# Unique Symbols Scanned:', globalAlertStats['Symbol'].nunique())
    print('')
    print('#########################################################')
    print('')
    
    return globalAlertStats

#####
# Look for the most frequently occuring symbols
#####
def findSymbolsWithHighFrequency(cleanAlertsDF):
    print('finding frequent Symbols!')
    # symbol, # alerts in last 3, 5, 8 days
    groupedAlerts = cleanAlertsDF.groupby(by='Symbol').count()
    print(groupedAlerts.head(10))


symbolList = [ 'AAPL', 'AMZN', 'BA', 'CCL', 'GM', 'MRNA', 
                'NET', 'NVDA', 'TWTR', 'CLF', 'FB', 'F']


def quickAnalysis(alertsDF):
    symbolAlerts = alertsDF

    sliceStats = generateSliceStats(symbolAlerts)
    sliceStats.sort_values(by='Percent Above 100', inplace=True, ascending=False)
    
    print('')
    print('Slices for Alert list')
    print(sliceStats)
    
    slices = sliceStats.loc[sliceStats['Total Alerts'] > 10]
    
    bestSlice = slices.loc[ (slices['Percent Above 100'] == slices['Percent Above 100'].max()) ]['Slice Name']
    
    alertsInBestSlice = getSliceAlerts(symbolAlerts, bestSlice.iloc[0])
    baseline = getSliceAlerts(symbolAlerts, 'baseline')

    print('')
    print('Printing Alerts in best slice:', bestSlice.iloc[0])
    print('')
    print(alertsInBestSlice.sort_values(by='Alert Date', ascending=False).head(30)[['Symbol', 'Strike', 'Option Type', 'Expiry', 'Ask', 'Max Gain %', 'Total $', 'IV', 'OI', 'Alert Date']])

    print('')
    print('Baseline Alerts')
    print('')
    print(baseline.sort_values(by='Alert Date', ascending=False).head(30)[['Symbol', 'Strike', 'Option Type', 'Expiry', 'Ask', 'Max Gain %', 'Total $', 'IV', 'OI', 'Alert Date']])

    plotReturns(alertsInBestSlice, title=bestSlice.iloc[0])
    plotReturns(baseline, 'Baseline')

#############
################### DEPRECATED
#############
def quickAnalysis_generalAlerts(sheetName):
    print('')
    print('Quick Analysis on:', sheetName)
    
    allAlerts = cleanAlertsData(alertsDF_map[sheetName])
    
    allAlerts_sliceStats = generateSliceStats(allAlerts, sheetName)
    
    selectSlices = allAlerts_sliceStats.loc[allAlerts_sliceStats['Total Alerts'] > 10]
    bestSlice = selectSlices.loc[ (selectSlices['Percent Above 100'] == selectSlices['Percent Above 100'].max()) ]['Slice Name']

    alertsInBestSlice = getSliceAlerts(allAlerts, bestSlice.iloc[0])

    print('')
    print('Slice Stats')
    print(allAlerts_sliceStats.sort_values(by='Percent Above 100', ascending=False))
    print('')
    print('Best Slice:', bestSlice.iloc[0])
    print(selectSlices.loc[ (selectSlices['Percent Above 100'] == selectSlices['Percent Above 100'].max())])
    print('')
    print('Alerts in Best Slice')
    print(alertsInBestSlice.sort_values(by='Alert Date', ascending=False).head(30)[['Symbol', 'Strike', 'Option Type', 'Expiry', 'Ask', 'Max Gain %', 'Total $', 'IV', 'OI', 'Alert Date']])

#####
# Summarize basic stats by 'watchlist' 
# for each watchlist plt scatters comparing all cols 
#####
def analyzeMyHunt(alertsDF):
    # for each unique watchlist in the passed in alertsDF
    # #alerts, avg max gain, std deviation of max gain
    summary = alertsDF.groupby(by='Watchlist').agg({ 'Max Gain %' : ['count', 'mean', 'min', 'max', 'std'] })

    print(summary)

    plotReturns(alertsDF)
    #result = df.groupby('Type').agg({'top_speed(mph)': ['mean', 'min', 'max']})




#globalSymbols = globalSymbolAnalysis()
#globalSymbols.sort_values(by='Percent Above 100', inplace=True, ascending=False)
#print(globalSymbols.loc[globalSymbols['Total Alerts'] > 20].head(20))

#quickAnalysis_Symbol('F')

#quickAnalysis_generalAlerts('ask<4;IV<150')

myAlerts = getAlerts('CRM')


quickAnalysis(myAlerts)

#analyzeMyHunt(myAlerts)
#print(myAlerts.columns)
#baseline = myAlerts.loc[(myAlerts['Watchlist'] == 'Low IV+DTE ($3M+)') & (myAlerts['Max Gain %'] < 800 ) & (myAlerts['Max Gain %'] > 50 ) ].drop(columns=['Underlying', 'Tier', 'Sector','Emojis', 'Watchlist', 'Alert Date', 'Strike', 'Max Loss %', 'Max Loss', 'Max Gain' ], axis=1) 

#findSymbolsWithHighFrequency(cleanAlertsData(alertsDF_map['ask1to4IVund200']))

######################

#mySliceAlerts = getSliceAlerts('SBUX', 'baseline')
#print(mySliceAlerts)
#print( generalAlertStats(cleanAlertsData(alertsDF_map['SBUX'])) )
#plotReturns(mySliceAlerts)

######################


#print(globalSymbols.loc[globalSymbols['Slice Name'] == 'CallsBullishAskSide'] )

#printTheseResults( sheetname, slice name)

#####
# Plotting clusters
#####
#elbowMethod(X_floatsOnly)
#plotCluster(X_floatsOnly, 2)

#####
# Plotting 
#####
# Plots scatter of each column 
#sns.pairplot(baseline, aspect=1.5)
#sns.pairplot(alertsDF_reduced, hue='Tier', aspect=1.5 )
#plotReturns(30)

#plt.show()
