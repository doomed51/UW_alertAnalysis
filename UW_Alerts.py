from os import P_DETACH, replace
from matplotlib.colors import LinearSegmentedColormap
from numpy.lib.npyio import load
from openpyxl import workbook, load_workbook
from openpyxl.worksheet import worksheet
from sklearn.cluster import KMeans

import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns


filePath = r"F:\workbench\UW_Alerts\UW_alerts.xlsx"
sheetName =  'CLF' #'asksidenotbearishAskUnder4' 'extraunusualIVunder200' #'extraunusual' 'ask4to6IVunder150' 'MRVL'  'ask1IV50to200' 
#filePath = r"F:\workbench\Sandbox\splittest.xlsx"

print('')
print('#########################################################')
print('Reading file:', filePath)
print('Success!')
print('#########################################################')
print('')

#load workbook
workbook = load_workbook(filename=filePath)
rawDF = pd.read_excel(filePath, sheetName)

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
# Cleaning up data 
#####

# drop: Action, Emojis columns
alertsDF = rawDF.drop(columns=['Actions','Emojis'], axis=1) 

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

###                                   ###
##### END OF DATA CLEAN UP SECTION  #####
###                                   ###

#####
# Adding compuited columns:
# 'DTE' Date to Expiry of the option when the alert was first fired 
alertsDF['DTE'] = (alertsDF['Expiry'] - alertsDF['Alert Date']).dt.days

#####
# Create slices of alertsDF data based on the % return
# for easier analysis 
#####
below0 = alertsDF.loc[alertsDF['Max Gain %'] <= 0]
below50 = alertsDF.loc[(alertsDF['Max Gain %'] <= 50) & (alertsDF['Max Gain %'] > 0)]
below100 = alertsDF.loc[(alertsDF['Max Gain %'] <= 100) & (alertsDF['Max Gain %'] > 50)]
over100 = alertsDF.loc[(alertsDF['Max Gain %'] <= 200) & (alertsDF['Max Gain %'] > 100)]
over200 = alertsDF.loc[(alertsDF['Max Gain %'] <= 1000) & (alertsDF['Max Gain %'] > 200)]
over1000 = alertsDF.loc[(alertsDF['Max Gain %'] > 1000)]

#####
# Cleaninig up the slices to remove unnneeded columns i.e. strings 
# to prepare for KMeans analysis 
#####
# all alerts preserved
X_allAlerts = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

# alerts based on optionType column i.e. Call or Put
X_optionType = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Sector', 'Underlying', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

# alerts based on sector column
X_Sector = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Underlying', '% Diff', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

# ALL string columns removed 
X_floatsOnly = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Alert Date', 'Tier', 'Max Gain' ], axis=1 )

#####
# Plot Max Gain % as the following: 
# 1. Call/Put highs over time 
# 2. highs histogram (call/put combined) 
#####
def plotReturns(bins): 
    fig, ax = plt.subplots(2)
    
    #sns.lineplot(x = alertsDF['Alert Date'], y = alertsDF['Max Gain %'], hue=alertsDF['Option Type'], )
    #ax[0] = sns.lineplot(x = alertsDF['Alert Date'], y = alertsDF['Max Gain %'], hue=alertsDF['Option Type'], )
    ax[0].plot(alertsDF['Alert Date'], alertsDF['Max Gain %'], label='Option Type')
    ax[1] = alertsDF['Max Gain %'].plot.hist(bins = bins, alpha=1)
    plt.show()

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
    #sns.pairplot( myDF, hue = 'Labels')
    #sns.scatterplot(myDF['DTE'], myDF['Max Gain %'], hue=myDF['Labels'],
    sns.scatterplot(myDF['Volume'], myDF['Max Gain %'], hue=myDF['Labels'],
    palette=sns.color_palette('hls', numClusters))
    plt.title('KMeans with 2 clusters')
    print(myDF.head())
    plt.show()

#####
# Use this function when you want to understand the alerts for one 
# particular symbol. 
#####
def analyzeSymbolAlerts():
    totalAlerts = alertsDF['Expiry'].count()
    alertsDF['Alert Date'] = alertsDF['Alert Date'].map( lambda t: t.strftime('%Y-%m-%d') )

    # percent calcs
    percentAbove1000 = (alertsDF.loc[(alertsDF['Max Gain %'] >= 1000)]['Volume'].count())
    percentAbove100 = (alertsDF.loc[(alertsDF['Max Gain %'] >= 100) & (alertsDF['Max Gain %'] < 1000)]['Volume'].count()) / totalAlerts * 100
    percentBelow10 = (alertsDF.loc[(alertsDF['Max Gain %'] <= 10)]['Volume'].count()) / totalAlerts * 100

    # calls vs. puts 
    callAlerts = alertsDF.loc[ alertsDF['Option Type'] == 'Call' ]
    PutAlerts = alertsDF.loc[ alertsDF['Option Type'] == 'Put' ]
    print('')
    print('###')
    print ('Printing Symbol-Alert Stats')
    print('###')
    print('')
    print ('Percent Stats on Max Gain ')
    print( 'Percent above 1000: %7.2f' % (percentAbove1000) )
    print( 'Percent above 100:  %7.2f' % percentAbove100 )
    print( 'Ppercent below 10:   %7.2f' % percentBelow10 )
    print('')
    print('Calls vs. Puts')
    print( 'Calls - Average Max Gain:   %7.2f' % callAlerts['Max Gain %'].mean() )
    print( 'Puts - Average Max Gain:    %7.2f' % PutAlerts['Max Gain %'].mean() )

    callAlerts = callAlerts[::-1] #flip the DF so time goes up left to right on the histogram plot
    callAlerts.plot(y = 'Max Gain %', x = 'Alert Date', kind = 'bar')
    plt.show()

#####
# Prints key stats on the any alerts dump
#####
def printAlertStats():
    totalAlerts = alertsDF['Alert Date'].count()
    totalPostiveAlerts = alertsDF.loc[alertsDF['Max Gain %'] > 0]['Alert Date'].count()
    totalNegativeAlerts = alertsDF.loc[alertsDF['Max Gain %'] <= 0]['Alert Date'].count()
    ITMalerts = alertsDF.loc[((alertsDF['Strike'] > alertsDF['Underlying']) & (alertsDF['Option Type'] == 'Put')) | ( (alertsDF['Strike'] < alertsDF['Underlying']) & (alertsDF['Option Type'] == 'Call') )]

    print('###########')
    print('Alert Stats for sheet:', sheetName)
    print('')
    # date range covered 
    print('Period start:', alertsDF['Alert Date'].min())
    print('Period End:', alertsDF['Alert Date'].max())
    print('')
    print('Total Alerts:', alertsDF['Alert Date'].count())
    print('Percent Positive:', totalPostiveAlerts / totalAlerts * 100)
    print('Percent Negative:', totalNegativeAlerts / totalAlerts * 100)
    print('')

    # total <50% , 100%, 200%, 1k+ 
    print('Bucketed Returns')
    print( '      < 0:', alertsDF.loc[(alertsDF['Max Gain %'] <= 0)]['Alert Date'].count() / totalAlerts * 100 )
    print( '   0 - 20:', alertsDF.loc[(alertsDF['Max Gain %'] <= 20) & (alertsDF['Max Gain %'] > 0)]['Alert Date'].count() / totalAlerts * 100 )
    print( '  21 - 50:', alertsDF.loc[(alertsDF['Max Gain %'] <= 50) & (alertsDF['Max Gain %'] > 20)]['Alert Date'].count() / totalAlerts * 100 )
    print( ' 51 - 100:', alertsDF.loc[(alertsDF['Max Gain %'] <= 100) & (alertsDF['Max Gain %'] > 50)]['Alert Date'].count() / totalAlerts * 100 )
    print( '101 - 200:', alertsDF.loc[(alertsDF['Max Gain %'] <= 200) & (alertsDF['Max Gain %'] > 100)]['Alert Date'].count() / totalAlerts * 100  )
    print( '201 - 500:', alertsDF.loc[(alertsDF['Max Gain %'] <= 500) & (alertsDF['Max Gain %'] > 200)]['Alert Date'].count() / totalAlerts * 100  )
    print( '     501+:', alertsDF.loc[(alertsDF['Max Gain %'] > 500)]['Alert Date'].count() / totalAlerts * 100  )

    print('')
    print('         Min Gain:', alertsDF['Max Gain %'].min())
    print('         Max Gain:', alertsDF['Max Gain %'].max())
    print(' Average max gain: ', alertsDF['Max Gain %'].mean())
    print(' Average max loss: ', alertsDF['Max Loss %'].mean())
    print('')
    print('Average Max Gain % - Calls:', (alertsDF.loc[alertsDF['Option Type'] == 'Call']['Max Gain %'].mean()))
    print('Average Max Gain % - Puts:', (alertsDF.loc[alertsDF['Option Type'] == 'Put']['Max Gain %'].mean()))
    print('')
    
    print('Alerts with Max Gain > 1000%')
    print(over1000.sort_values(['Alert Date']))
    print('')
    print('Alerts with Max Gain > 200%')
    print(over200.sort_values(['Alert Date']))
    print('')
    print('Alerts with Max Gain < 0%')
    print(below0.sort_values(['Alert Date']))
    print('')
    print('Alerts over 50%')
    print(alertsDF.loc[alertsDF['Max Gain %'] > 50])
    print('')
    print('last 10 alerts')
    print(alertsDF.head(10))
    print('')
    print('Alerts with DTE < 5')
    print(alertsDF.loc[alertsDF['DTE'] < 5])
    print('')
    print( ITMalerts.sort_values(by=['Alert Date'], ascending=True) )
    print('')
    
    
#####
# PRINTING stats
#####

# Easier to read table with select columns 
alertsDF_reduced = alertsDF[['Alert Date', 'Option Type', 'Strike', 'Underlying', 'DTE', 'Expiry', 'Tier', 'OI', 'Volume', 'Max Loss %', 'Max Gain %']]

analyzeSymbolAlerts()
printAlertStats()

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
#plotReturns(30)

#plt.show()




