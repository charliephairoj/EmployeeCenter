#!/usr/local/bin/python
# -*- coding: utf-8 -*-
# Open Excel file from a user imput

import xlrd
import xlwt
from xlwt import *
import math
#filename = raw_input("Enter Excel file name with extension (.xls) and path")
filename = "DR_AP.xlsx"
oldbook = xlrd.open_workbook(filename, encoding_override="utf_8")
newbook = xlwt.Workbook()

replace_dict = {
    u"ลี่หยาง จำกัด": u"Liyang Co., Ltd.",
    u"พีที. อินเฟอร์เมชั่น แอนด์ คอมพิวเตอร์ ซัพพลาย": u"PT Information & Computer Supplies",
    u"พี วิชั่น (ไทยแลนด์)": "IP Vision (Thailand)",
    u"ฟูจิ ซีร็อกซ์ ( ประเทศไทย )": "Fuji Xerox (Thailand)",
    u"มาจอง โปรดักส์ จำกัด": "Majong Co., Ltd.",
    u"ไมโรโทน (ประเทศไทย) จำกัด": "Maritone Co., Ltd",
    u"รปภ.ไทย จำกัด" : "Thai Guard Co., Ltd.",
    u"วี.เอส.วี.เพนท์ แอนด์ เคมีคอล": "VSV Paint and Chemical (Sunyu)",
    u"ศิริไกรอุตสาหการ": "Sirikrai Industrial",
    u"สยาม เค.ซี. เมทัล อินดัสทรี จำกัด": "Siam KC Industries Co., Ltd.",
    u"สยามวู้ดแลนด์ จำกัด": "Siam Woodland Co., Ltd.",
    u"ห้างกระจกตังน้ำ": "Tangnam Glass",
    u"อาร์ต คัลเลอร์ ดีไซน์ จำกัด": "Art Color Design Co. Ltd",
    u"แอ็พพลาย ดีบี อินดัสเตรียล จำกัด": "Applied DB Industrial Co., Ltd.",
    u"อยุธยา แคปปิตอล ออโต้ ลีส": "Ayudhya Capital Auto Lease",
    u"เอ็น.เอส.ซี.สตีล จำกัด": "NAC Steel Co., Ltd.",
    u"ฮิตาชิ แคปปิตอล (ประเทศไทย)": "Hitachi Capital Co., Ltd.",
    u"เฮเฟเล่ (ประเทศไทย)": u"Häfele (Thailand)",
    u"รวมทั้งสิ้น": "Total",
    u"การไฟฟ้าส่วนภูมิภาค": "Electricity",
    u"ชัยเจริญมัลติเทรดดิ้ง": "Chaicharoen Multi Trading",
    u"ซันเพนท": "Sun Panut",
    u"เซี่ยหลง จำกัด": "Xialong Co., Ltd.",
    u"ซี แอนด์ เอส เวลตี้ ซัพพลาย": "C & S Wealthy Supplies",
    u"ฐาปนินทร์ จำกัด": "Thapanin Co., Ltd.",
    u"ดีเอชแอล เอ๊กซ์เพรส อินเตอร์เนชั่นแนล": "DHL Express International",
    u"สีไทยกันไซเพ้นท์ จำกัด": "Thai Kansai Paint Co., Ltd.",
    u"ทีจีดี ออโตเมติก ดอร์ส จำกัด": "TGD Automatic Doors Co., Ltd.",
    u"ไทยดีนุช เทรดดิ้ง": "Thai Dee Nut Trading Co., Ltd.",
    u"เท็กซ์ไทล์ แกลลอรี่ จำกัด": "Textile Gallery Co., Ltd.",
    u"ที.พี.ไดมอนด์เพ้นท": "TP Diamond Paint",
    u"ที.พลัส มาร์เก็ตติ้ง": "T Plus Marketing",
    u"ไทยโฟม อินดัสตร": "Thai Foam Industries",
    u"ไท-โย เพนท์ ( ประเทศไทย )": "Tai Yo Paint (Thailand)",
    u"ไทย เวิร์คท๊อป จำกัด": "Thai Worktop Co., Ltd.",
    u"ที.เอส.ที.อินเตอร์โปรดักส": "TST International Products",
    u"บางกอกโฟม จำกัด": "Bangkok Foam Co., Ltd.",
    u"เบทเตอร์แพค จำกัด": "Better Pack Co., Ltd.",
    u"บลู อินเตอร์เนชั่นแนล": "Blue International",
    u"พรีซิชั่นไลน์": "Precisionline",
    u"ชื่อเจ้าหนี้": u"Creditor/Vendor",
    u"จะครบกำหนด": "Due",
    u"เกินกำหนด": "Overdue",
    u"ยอดหนี้รวม": "Total",
    u"วัน": "Days",
    u"เกิน": "Over",
    u"ภายใน": "Within",
    u"ผู้จำหน่ายจาก": "Supplier",
    u"รายงานวิเคราะห์อายุหนี้แยกตามเจ้าหนี้": "Account Payables",
    u"บริษัท เดลา โรเบียร (ประเทศไทย) จำกัด": "Dellarobbia (Thailand) Co., Ltd."
    
}

style = XFStyle()

# For all the sheets in the workbook
for sheetname in oldbook.sheet_names():
    oldsheet = oldbook.sheet_by_name(sheetname)
    newsheet = newbook.add_sheet(sheetname)

    # For all the rows and all the columns in an excel
    for ii in range(oldsheet.nrows):
        for jj in range(oldsheet.ncols):
            style = easyxf('font: height 220;')
            # Replace
            CellString=oldsheet.cell(ii, jj).value
            try:
                for key, text in replace_dict.items():
                    try:
                        if key in CellString:
                            CellString = CellString.replace(key, text)
            
                    except TypeError:
                        pass
                    
            except AttributeError:
                pass
            
            for test in ['day']:
                try:
                    if test in CellString.lower():
                        style = easyxf('font: bold true, height 260;')
                except (TypeError, AttributeError):
                    pass
                    
            for test in ['creditor', 'due', 'total']:
                try:
                    if test in CellString.lower():
                        style = easyxf('font: bold true, underline true, height 320; align: horz center')
                except (TypeError, AttributeError):
                    pass
                    
            newsheet.write(ii, jj, CellString, style=style)
            
        #Adjust row height
        newsheet.row(ii).height = int(math.floor(newsheet.row(ii).height * 2))

    #Adjust witdth
    newsheet.col(0).width = newsheet.col(0).width * 3
    for i in xrange(1, 10):
        newsheet.col(i).width = int(math.floor(newsheet.col(i).width * 1.40))
    
# Save the file in a desired location with the desired name
#savelocation = raw_input("Enter a new path and file name with extension (.xls) to save the new Excel spread sheet ")
savelocation = "test.xls"
newbook.save(savelocation)
            
"""
def replace_text(text):
    replace_dict = {u"ลี่หยาง จำกัด" : "Liyang Co., Ltd."}
    for key, text in replace_dict.items():
        text.replace(key, text)
        
    return text
    
    
with open('DR_AP.xlsx', 'rb') as file:
    text = file.read()
    text = replace_text(text)
    
with open('DR_AP(translated).xlsx', 'wb') as w:
    w.write(text)
"""
    