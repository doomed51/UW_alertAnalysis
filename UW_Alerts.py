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

# Location of the file that contains the alerts dump
filePath_symbolAlerts = r"F:\workbench\UW_Alerts\UW_alerts_symbols.xlsx"
filePath_aggregatedAlerts = r"F:\workbench\UW_Alerts\UW_alerts.xlsx"
filePath = filePath_symbolAlerts

print('')
print('#########################################################')
print('Loading file:', filePath)

#load workbook
start = time.perf_counter()
workbook = load_workbook(filename=filePath)
alertsDF_map = pd.read_excel(filePath, sheet_name=None)
end = time.perf_counter()

print('')
print('Success!')
print(f"Elapsed Time: {end - start:0.4f} seconds")
print()
print('#########################################################')
print('')



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
    alertsDF['Alert Date'] = alertsDF['@'].str[:-7]
    alertsDF['Alert Date'] = pd.to_datetime(alertsDF['Alert Date'])

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
    alertsDF[['Max Gain', 'Max Gain %']] = alertsDF['Contract High'].str.split(' ', expand=True)
    alertsDF['Max Gain'] = alertsDF['Max Gain'].str.replace('$', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace(')', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace('(', '', regex=True)
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace('%', '', regex=True)
    alertsDF['Max Gain'] = alertsDF['Max Gain'].astype('float')
    alertsDF['Max Gain %'] = alertsDF['Max Gain %'].astype('float')

    # Clean up Max Loss columns
    # split into individual $ and % columns
    # recast columns to ensure they are floats
    alertsDF[['Max Loss', 'Max Loss %']] = alertsDF['Contract Low'].str.split(' ', expand=True)
    alertsDF['Max Loss'] = alertsDF['Max Loss'].str.replace('$', '', regex=True)
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace(')', '', regex=True)
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace('(', '', regex=True)
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace('%', '', regex=True)
    alertsDF['Max Loss'] = alertsDF['Max Loss'].astype('float')
    alertsDF['Max Loss %'] = alertsDF['Max Loss %'].astype('float')

    # making sure no NaN's 
    alertsDF.fillna(0, inplace=True)

    # drop the old columns
    alertsDF = alertsDF.drop(columns=['Contract High','Contract Low', '@'], axis=1)

    #####
    # Adding compuited columns:
    # 'DTE' Date to Expiry of the option when the alert was first fired 
    alertsDF['DTE'] = (alertsDF['Expiry'] - alertsDF['Alert Date']).dt.days

    return alertsDF

#####
# Create slices of alertsDF data based on the % return
# for easier analysis 
#####
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
def plotReturns(bins, alertsDF): 
    fig, ax = plt.subplots(2)
    ax[0].plot(alertsDF['Alert Date'], alertsDF['Max Gain %'], label='Option Type')
    ax[1] = alertsDF['Max Gain %'].plot.hist(bins = bins, alpha=1)
    plt.show()

#####
# Cleaninig up the slices to remove unnneeded columns i.e. strings 
# to prepare for KMeans analysis 
#####
def prepAlertsDataForKMeans(alertsDF, type='all'):

    dataframeOfFloats = pd.DataFrame()

    if type == 'all':
        dataframeOfFloats = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )
    

    elif type == 'optionType':
        dataframeOfFloats = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Sector', 'Underlying', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

    elif type == 'sector':
        dataframeOfFloats = alertsDF.drop(['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Underlying', '% Diff', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

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
def generalAlertStats(alertsDF, sliceName = 'default', sheetName = 'default'):
    totalAlerts = alertsDF['Expiry'].count()
    totalPostiveAlerts = alertsDF.loc[alertsDF['Max Gain %'] > 0]['Alert Date'].count()
    totalNegativeAlerts = alertsDF.loc[alertsDF['Max Gain %'] <= 0]['Alert Date'].count()

    # if the # of unique symbols > 1
    colName = ''
    if sheetName == 'default':
        colName = 'Symbol'
        colVal = alertsDF.iloc[1]['Symbol']
    else:
        colName = 'Sheet Name'
        colVal = sheetName

    percentStatsData = {
        #'Symbol': [alertsDF['Symbol']],
        colName: [ colVal ],
        
        'Slice Name': [sliceName],
        
        'Period Start': [alertsDF['Alert Date'].min().strftime('%Y-%m-%d')], 
        
        'Period End': [alertsDF['Alert Date'].max().strftime('%Y-%m-%d')],
        
        'Total Alerts': [alertsDF['Alert Date'].count()], 
        
        'Percent Positive': [totalPostiveAlerts / totalAlerts * 100],

        'Percent Above 100': [alertsDF.loc[(alertsDF['Max Gain %'] >= 20)]['Alert Date'].count() / totalAlerts * 100],
        
        'Percent Negative': [totalNegativeAlerts / totalAlerts * 100],
        
        'Gain % (Calls)': [alertsDF.loc[alertsDF['Option Type'] == 'Call']['Max Gain %'].mean()],
        
        'Gain % (Puts)': [alertsDF.loc[alertsDF['Option Type'] == 'Put']['Max Gain %'].mean()],
        
        '<0' : [alertsDF.loc[(alertsDF['Max Gain %'] <= 0)]['Alert Date'].count() / totalAlerts * 100],
        
        '0-20': [alertsDF.loc[(alertsDF['Max Gain %'] <= 20) & (alertsDF['Max Gain %'] > 0)]['Alert Date'].count() / totalAlerts * 100],
        
        '21-50': [alertsDF.loc[(alertsDF['Max Gain %'] <= 50) & (alertsDF['Max Gain %'] > 20)]['Alert Date'].count() / totalAlerts * 100],
        
        '51-100': [alertsDF.loc[(alertsDF['Max Gain %'] <= 100) & (alertsDF['Max Gain %'] > 50)]['Alert Date'].count() / totalAlerts * 100],
        
        '101-200': [alertsDF.loc[(alertsDF['Max Gain %'] <= 200) & (alertsDF['Max Gain %'] > 100)]['Alert Date'].count() / totalAlerts * 100],
        
        '201-500': [alertsDF.loc[(alertsDF['Max Gain %'] <= 500) & (alertsDF['Max Gain %'] > 200)]['Alert Date'].count() / totalAlerts * 100],
        
        '500+': [alertsDF.loc[(alertsDF['Max Gain %'] > 500)]['Alert Date'].count() / totalAlerts * 100]

    }
    percentStats = pd.DataFrame(percentStatsData)
    percentStats = percentStats.round(2)
    return percentStats

#####
# Creates a dataframe with different views of the alerts dataset
# new DF = [ Symbol, Slice, stats pulled from generalAlertStat():::]
#####
def createViews_alerts(alertsDF, sheetName = 'default'):
    
    alertSlices = generalAlertStats(alertsDF, 'Baseline', sheetName=sheetName)
    
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Daily $ Vol'] < 100000) & (alertsDF['OI'] < alertsDF['Volume']))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'$vol<1K; OI<Vol', sheetName=sheetName ))
    
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['DTE'] > 20))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'DTE>20', sheetName=sheetName ))
    
    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['DTE'] < 20))]
    if not alertsDF_reduced.empty:
         alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'DTE<20', sheetName=sheetName ))

    alertsDF_reduced = alertsDF.loc[ ( (alertsDF['Tier'] == 'premium') & (alertsDF['DTE'] > 20))]
    if not alertsDF_reduced.empty:
        alertSlices = alertSlices.append(generalAlertStats(alertsDF_reduced,'Premium; DTE>20', sheetName=sheetName ))
    
    return alertSlices

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
            createViews_alerts(
            cleanAlertsData(
                alertsDF_map[mySheetName])), ignore_index=True
            )
        
        else:
            alertsDF_combined = alertsDF_combined.append(
            createViews_alerts(
            cleanAlertsData(
                alertsDF_map[mySheetName]), sheetName=mySheetName), ignore_index=True
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
# Similar to globalSymbolAnalysis except for general alert dumps that
# contain different Sybols
#####
def generalAlertsAnalysis():
    print('')
    print('#########################################################')
    print('Analyzing multi-symbol alerts')

symbolList = [ 'AAPL', 'AMZN', 'BA', 'CCL', 'GM', 'MRNA', 
                'NET', 'NVDA', 'TWTR', 'CLF', 'FB', 'F']

#myAlerts = compareAlertSlices(symbolList)
#print(myAlerts.head(20))

globalSymbols = globalSymbolAnalysis()
print(globalSymbols.loc[globalSymbols['Total Alerts'] > 20].head(20))

#####
# Plotting clusters
#####
#elbowMethod(X_floatsOnly)
#plotCluster(X_floatsOnly, 2)

#####
# Plotting 
#####
# Plots scatter of each column 
#sns.pairplot(X_optionType, hue='Option Type', aspect=1.5)
#sns.pairplot(alertsDF_reduced, hue='Tier', aspect=1.5 )
#plotReturns(30)

#plt.show()
