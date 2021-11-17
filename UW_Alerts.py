from os import P_DETACH, replace
from numpy.lib.npyio import load
from openpyxl import workbook, load_workbook
from openpyxl.worksheet import worksheet
from sklearn.cluster import KMeans

import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns


filePath = r"F:\workbench\UW_Alerts\UW_alerts.xlsx"
#filePath = r"F:\workbench\Sandbox\splittest.xlsx"

print('')
print('#########################################################')
print('Reading file:', filePath)
print('Success!')
print('#########################################################')
print('')

#load workbook
workbook = load_workbook(filename=filePath)
rawDF = pd.read_excel(filePath, 'ask1IV50to200')

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


# Clean up data
# drop: Action, Emojis
alertsDF = rawDF.drop(columns=['Actions','Emojis'], axis=1) 
alertsDF['Time'] = pd.to_datetime(alertsDF['Time'])
alertsDF['Option'].str.strip()

alertsDF['Option'] = alertsDF['Option'].astype('str')
alertsDF['Option'] = alertsDF['Option'].str.strip()

#splt the Option col into symbol and strike
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

# < 0
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
# print statistical info
#####
#print(alertsDF.head(10))
#print(alertsDF.describe())

#print('average max gain', alertsDF['Max Gain %'].mean())


#####
# Plots and Graphs
#####

#alertsDF.plot.scatter(y = 'Max Loss %', x = 'IV')
#alertsDF.plot.scatter(y = 'Max Loss %', x = 'Underlying')
#alertsDF.plot.scatter(y = 'Max Loss %', x = 'Max Gain %')

#alertsDF.plot.hist('Max Gain %', bins = 20)
#alertsDF['Max Gain %'].plot.hist(bins=80)
#alertsDF['Max Loss %'].plot.hist(bins=80)

#####
# Data slices for analysis
#####
X_allAlerts = alertsDF.drop( ['Symbol', 'Expiry', 'Max Loss', 'Max Loss %', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

X_optionType = below0.drop( ['Symbol', 'Expiry', 'Max Loss', 'Max Loss %', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

X_Sector = over200.drop( ['Symbol', 'Expiry', 'Max Loss', 'Max Loss %', 'Option Type', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

X_floatsOnly = below0.drop( ['Symbol', 'Expiry', 'Max Loss', 'Max Loss %', 'Option Type', 'Sector', 'Underlying', '% Diff', 'OG ask', 'Time', 'Tier', 'Max Gain' ], axis=1 )

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
# Clustering
#####
def plotCluster(myDF, numClusters):
    km3 = KMeans(n_clusters = numClusters).fit(myDF)
    myDF['Labels'] = km3.labels_ 
    
    plt.figure(figsize=(12, 8))
    sns.pairplot( myDF, hue = 'Labels')

    plt.show()

#elbowMethod(X_floatsOnly)
plotCluster(X_floatsOnly, 3)

#print(X_allAlerts.head())

#####
# plotting 
#####
# Plots scatter of each column 
#sns.pairplot(X_optionType, hue='Option Type', aspect=1.5)

