from os import P_DETACH, replace
from numpy.lib.npyio import load
from openpyxl import workbook, load_workbook
from openpyxl.worksheet import worksheet
from sklearn.cluster import KMeans

import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns


filePath = r"F:\workbench\UW_Alerts\UW_alerts.xlsx"
sheetName =  'SABR'  #'ask1IV50to200' 
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
alertsDF['Time'] = alertsDF['Time'].str[:-7]
alertsDF['Time'] = pd.to_datetime(alertsDF['Time'])

# remove trailing spaces 
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
alertsDF[['Max Gain', 'Max Gain %']] = alertsDF['Max Gain'].str.split(' ', expand=True)
alertsDF['Max Gain'] = alertsDF['Max Gain'].str.replace('$', '', regex=True)
alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace(')', '', regex=True)
alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace('(', '', regex=True)
alertsDF['Max Gain %'] = alertsDF['Max Gain %'].str.replace('%', '', regex=True)
alertsDF['Max Gain'] = alertsDF['Max Gain'].astype('float')
alertsDF['Max Gain %'] = alertsDF['Max Gain %'].astype('float')

# Clean up Max Loss columns
# split into individual $ and % columns
# recast columns to ensure they are floats 
alertsDF[['Max Loss', 'Max Loss %']] = alertsDF['Max Loss'].str.split(' ', expand=True)
alertsDF['Max Loss'] = alertsDF['Max Loss'].str.replace('$', '', regex=True)
alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace(')', '', regex=True)
alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace('(', '', regex=True)
alertsDF['Max Loss %'] = alertsDF['Max Loss %'].str.replace('%', '', regex=True)
alertsDF['Max Loss'] = alertsDF['Max Loss'].astype('float')
alertsDF['Max Loss %'] = alertsDF['Max Loss %'].astype('float')

alertsDF.fillna(0, inplace=True)

###                                   ###
##### END OF DATA CLEAN UP SECTION  #####
###                                   ###

#####
# Adding compuited columns:
# 'DTE' Date to Expiry of the option when the alert was first fired 
alertsDF['DTE'] = (alertsDF['Expiry'] - alertsDF['Time']).dt.days



#####
# Create slices of alertsDF data based on the % return
# for further analysis 
#####
# <= 0
below0 = alertsDF.loc[alertsDF['Max Gain %'] <= 0]

# 0 - 50
below50 = alertsDF.loc[(alertsDF['Max Gain %'] <= 50) & (alertsDF['Max Gain %'] > 0)]

# 50 - 100
below100 = alertsDF.loc[(alertsDF['Max Gain %'] <= 100) & (alertsDF['Max Gain %'] > 50)]

# 100 - 200
over100 = alertsDF.loc[(alertsDF['Max Gain %'] <= 200) & (alertsDF['Max Gain %'] > 100)]

# 200 - 1000
over200 = alertsDF.loc[(alertsDF['Max Gain %'] <= 1000) & (alertsDF['Max Gain %'] > 200)]

# > 1000
over1000 = alertsDF.loc[(alertsDF['Max Gain %'] > 1000)]

#####
# Cleaninig up the slices to remove unnneeded columns i.e. strings 
# to prepare for KMeans analysis 
#####

# all alerts preserved
X_allAlerts = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

# alerts based on optionType column i.e. Call or Put
X_optionType = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Sector', 'Underlying', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

# alerts based on sector column
X_Sector = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

# ALL string columns removed 
X_floatsOnly = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

#####
# Plot returns over time 
#####
def plotReturns(bins): 
    # max gain on calls & puts on 1 chart 
    
    #sns.lineplot(x = alertsDF['Time'], y = alertsDF['Max Gain %'], hue=alertsDF['Option Type'], )
    
    alertsDF['Max Gain %'].plot.hist(bins = bins, alpha=1)

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
# PRINTING stats
#####
print('Min Gain:', alertsDF['Max Gain %'].min())
print('Max Gain:', alertsDF['Max Gain %'].max())
print('Median:', alertsDF['Max Gain %'].median())

#print(alertsDF.cov())
#print(alertsDF.describe())

print('Average max gain: ', alertsDF['Max Gain %'].mean())
print('Average max loss: ', alertsDF['Max Loss %'].mean())

#####
# Plotting 
#####
# Plots scatter of each column 
#sns.pairplot(X_optionType, hue='Option Type', aspect=1.5)

#alertsDF.plot.scatter(y = 'Max Loss %', x = 'IV')
#alertsDF.plot.scatter(y = 'Max Loss %', x = 'Underlying')
alertsDF.plot.line(x = 'Time', y = 'Max Gain %')

#alertsDF.plot.hist('Max Gain %', bins = 20)
#alertsDF['Max Gain %'].plot.hist(bins=80)
#alertsDF['Max Loss %'].plot.hist(bins=80)
alertsDF_reduced = alertsDF[['Time', 'Option Type', 'Strike', 'Underlying', 'DTE', 'Expiry', 'Tier', 'OI', 'Volume', 'Max Loss %', 'Max Gain %']]
ITMalerts = alertsDF_reduced.loc[((alertsDF_reduced['Strike'] > alertsDF_reduced['Underlying']) & (alertsDF_reduced['Option Type'] == 'Put')) | ( (alertsDF_reduced['Strike'] < alertsDF_reduced['Underlying']) & (alertsDF_reduced['Option Type'] == 'Call') )]

print ( alertsDF_reduced.sort_values(by=['Time'], ascending=True) )
print('')
print('ITM Alerts')
print ( ITMalerts.sort_values(by=['Time'], ascending=True) )

#####
# Plotting clusters
#####
#elbowMethod(X_floatsOnly)
#plotCluster(X_floatsOnly, 2)

#plt.show()
#plotReturns(10)



