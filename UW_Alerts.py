from os import P_DETACH, replace
from numpy.lib.npyio import load
import pandas as pd 
import matplotlib.pyplot as plt

from openpyxl import workbook, load_workbook
from openpyxl.worksheet import worksheet

filePath = r"F:\workbench\UW_Alerts\UW_alerts.xlsx"
#filePath = r"F:\workbench\Sandbox\splittest.xlsx"
print('#########################################################')
print('')
print('Reading file:', filePath)
print('')

#load workbook
workbook = load_workbook(filename=filePath)
rawDF = pd.read_excel(filePath, 'Sheet1')

print('Success!')
print('#####################################################')

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

# Remove all special symbols 
spec_chars = ["$", "!",'"',"#","%","&","'","(",")",
              "*","+",",","-",".","/",":",";","<",
              "=",">","?","@","[","\\","]","^","_",
              "`","{","|","}","~","–"]

#for char in spec_chars:
alertsDF['Option'] = alertsDF['Option'].str.strip()
alertsDF['Option'] = alertsDF['Option'].astype('str')

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

# split up the cleaned up alertsDF into the following
# < 50%
# < 100% 
# >= 100%
# >= 200%
# >= 1000%



#####
# print statistical info
#####
print(alertsDF.head(10))
print(alertsDF.describe())

print('average max gain', alertsDF['Max Gain %'].mean())


#####
# Plots and Graphs
#####

#alertsDF.plot.scatter(y = 'Max Loss %', x = 'IV')
#alertsDF.plot.scatter(y = 'Max Loss %', x = 'Underlying')
#alertsDF.plot.scatter(y = 'Max Loss %', x = 'Max Gain %')

#alertsDF.plot.hist('Max Gain %', bins = 20)
#alertsDF['Max Gain %'].plot.hist(bins=80)
alertsDF['Max Loss %'].plot.hist(bins=80)

plt.show()