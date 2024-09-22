import re
import sys
import math
import glob
import os.path
from pathlib import Path
import yfinance as yf
import pandas as pd
import warnings
import inspect
import numpy as np
import openpyxl
from datetime import datetime
from datetime import timedelta

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

REQUIRED_FILES = ['assets.xlsx', 'b3_dividend_data.xlsx']

def parseArguments(system_arguments) :

    if len(system_arguments) == 1 :
        raise TypeError("empty arguments!")

    arguments = {}

    template_path = Path(system_arguments[1])

    if not template_path.exists() :
        raise TypeError("Folder path does not exist!")

    if not template_path.is_dir() :
        raise TypeError("Template path does not lead to a folder!")

    all_csv_files_from_folder = glob.glob(system_arguments[1] + "/*.xlsx")

    for index in range(len(all_csv_files_from_folder)):
        all_csv_files_from_folder[index] = os.path.basename(all_csv_files_from_folder[index])

    if len(set(all_csv_files_from_folder) & set(REQUIRED_FILES)) < len(REQUIRED_FILES):
        raise TypeError("Not all required template files exist on " + system_arguments[1] + ", check the documentation for more information!")

    return system_arguments[1]

def getAssetsFromTemplate(template_path) :

    try:

        excel_data_df = pd.read_excel(template_path+REQUIRED_FILES[0], sheet_name="assets")
        assets = excel_data_df.to_numpy()

    except Exception as ex:
        raise TypeError("Invalid " + REQUIRED_FILES[0] + " !")

    if len(assets) == 0:
        raise TypeError("Empty " + REQUIRED_FILES[0] + " !")

    validateTemplate(assets)

    result_assets = {}

    for index_line in range(len(assets)):

        result_assets[assets[index_line][0]] = assets[index_line][1]

    return result_assets

def validateTemplate(assets) :

    if len(assets[0]) != 2 :
        raise TypeError("Invalid column structure on " + REQUIRED_FILES[0] + " !")

    for index_line in range(len(assets)):

        if not type(assets[index_line][0]) is str or not type(assets[index_line][1]) is float :
            raise TypeError("Invalid column type on line " + index_line + " from " + REQUIRED_FILES[0] + " !")

    return assets

def getDividendsFromTemplate(template_path) :

    try:

        excel_data_df = pd.read_excel(template_path+REQUIRED_FILES[1], sheet_name="Proventos Recebidos")
        dividends = excel_data_df.to_numpy()

    except Exception as ex:
        raise TypeError("Invalid " + REQUIRED_FILES[0] + " !")

    if len(dividends) == 0:
        raise TypeError("Empty " + REQUIRED_FILES[0] + " !")

    result_dividends = []

    for index_line in range(len(dividends)):

        if not pd.isna(dividends[index_line][0]) :

            line = {}

            tokens = dividends[index_line][0].split("-")
            line["ticker"] = tokens[0].split()[0]
            line["payday"] = datetime.strptime(dividends[index_line][1], "%d/%m/%Y")
            line["broker"] = dividends[index_line][3]
            line["number_of_shares"] = int(dividends[index_line][4])
            line["payment_by_share"] = dividends[index_line][5]
            line["net_payment"] = dividends[index_line][6]

            result_dividends.append(line)

    return result_dividends

def prepareDataToRequest(dividends) :

    request_data = {}

    for index_line in range(len(dividends)):

        payday_date = dividends[index_line]["payday"]

        if request_data.get(payday_date) is None :

            request_data[payday_date] = []

        yf_ticker = dividends[index_line]["ticker"] + ".SA"

        if not yf_ticker in request_data[payday_date] :
            request_data[payday_date].append(yf_ticker)

    return request_data

def getAssetsData (request_data) :

    result = {}

    for date, assets in request_data.items() :

        date_start = date.strftime("%Y-%m-%d")
        date_end = date + timedelta(days=1)
        date_end = date_end.strftime("%Y-%m-%d")

        assets_data = yf.download(assets, start=date_start, end=date_end)
        assets_data = assets_data['Close'].to_numpy()[0]

        result[date] = {}

        if isinstance(assets_data, np.ndarray) :

            for index in range(len(assets)):

                result[date][assets[index]] = assets_data[index]

        else :

            result[date][assets[0]] = assets_data

    return result

def prepareExcelData (assets, dividends, assets_data) :

    excel_data = []
    excel_data.append(["Date", "Base Asset", "Number Of Shares", "Gross Income", "Taxes", "Net Income", "Net Income By Share", "Share Price On Date", "Net Dividend Yield", "Average Price On Date", "Dividend Yield On Net Cost", "Type", "Broker"])

    for index_line in range(len(dividends)):

        line = []
        line.append(dividends[index_line]["payday"].strftime("%d/%m/%Y"))
        line.append(dividends[index_line]["ticker"])
        line.append(dividends[index_line]["number_of_shares"])
        gross_income = round(dividends[index_line]["payment_by_share"] * dividends[index_line]["number_of_shares"], 2)
        line.append(gross_income)
        taxes = round(gross_income - dividends[index_line]["net_payment"], 2)
        line.append(taxes)
        line.append(round(dividends[index_line]["net_payment"], 2))
        net_income_by_share = round(dividends[index_line]["net_payment"]/dividends[index_line]["number_of_shares"], 2)
        line.append(net_income_by_share)
        share_price_on_date = round(assets_data[dividends[index_line]["payday"]][dividends[index_line]["ticker"] + ".SA"], 2)
        line.append(share_price_on_date)
        line.append(net_income_by_share/share_price_on_date)
        average_price_on_date = round(assets[dividends[index_line]["ticker"]], 2)
        line.append(average_price_on_date)
        line.append(net_income_by_share/average_price_on_date)
        numbers = re.findall('\d+\.\d+|\d+', dividends[index_line]["ticker"])
        line.append(numbers[0])
        line.append(dividends[index_line]["broker"])
        excel_data.append(line)

    return excel_data

def createExcelFile (excel_data, template_path) :

    workbook = openpyxl.Workbook()
    sheet = workbook.active

    for row in excel_data:
        sheet.append(row)

    workbook.save(template_path + "my_excel_file.xlsx")

def main():

    #data = yf.download(["AAPL", "MSFT"], start="2024-09-14", end="2024-09-14")
    #print(data['Close'].to_numpy())
    #sys.exit(0)

    try:

        template_path = parseArguments(sys.argv)
        assets = getAssetsFromTemplate(template_path)
        dividends = getDividendsFromTemplate(template_path)

    except Exception as ex:

        print("Something went wrong when trying to get template information ...\n"+ str(ex))
        sys.exit(0)

    try:

        request_data = prepareDataToRequest(dividends)
        assets_data = getAssetsData(request_data)

    except Exception as ex:

        print("Something went wrong when trying to get yfinance data ...\n"+ str(ex))
        sys.exit(0)

    try:

        excel_data = prepareExcelData(assets, dividends, assets_data)
        createExcelFile(excel_data, template_path)

    except Exception as ex:

        print("Something went wrong when trying to create excel file ...\n"+ str(ex))
        sys.exit(0)


main()