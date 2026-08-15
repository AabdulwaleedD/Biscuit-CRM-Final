import pandas as pd, random
from pathlib import Path
from datetime import datetime, timedelta
random.seed(2026)
base=Path(__file__).parent/'data'
today=datetime(2026,8,14)
customers=pd.read_csv(base/'customers.csv').drop_duplicates('Customer ID')
products=pd.read_csv(base/'products.csv').drop_duplicates('Product ID')
products['Selling Price']=pd.to_numeric(products['Selling Price'],errors='coerce').fillna(5000)
products['Cost Price']=pd.to_numeric(products['Cost Price'],errors='coerce').fillna(products['Selling Price']*.75)
# Inventory ledger
inv=[]; stock={}; n=1
for _,p in products.iterrows():
    opening=random.randint(500,2200); received=random.randint(100,1200)
    stock[p['Product ID']]=opening+received
    inv.append([f'STOCK-{n:06d}',(today-timedelta(days=60)).strftime('%Y-%m-%d'),p['Product ID'],p['Product Name'],'Opening Stock',opening,f'OPEN-{p["Product ID"]}','Main Warehouse','Demo Administrator','Initial demo stock']); n+=1
    inv.append([f'STOCK-{n:06d}',(today-timedelta(days=random.randint(1,45))).strftime('%Y-%m-%d'),p['Product ID'],p['Product Name'],'Stock Received',received,f'GRN-{n:06d}','Main Warehouse','Demo Administrator','Demo replenishment']); n+=1
# Sales/invoices/payments
sales=[]; items=[]; invoices=[]; payments=[]; payno=1
for i in range(1,121):
    sid=f'SALE-2026-{i:06d}'; iid=f'INV-2026-{i:06d}'; dt=today-timedelta(days=random.randint(0,59))
    c=customers.iloc[random.randrange(len(customers))]; p=products.iloc[random.randrange(len(products))]
    qty=random.randint(5,45); price=float(p['Selling Price']); subtotal=qty*price; disc=round(subtotal*random.choice([0,0,.02,.03]),-2); total=round(subtotal-disc,2)
    pay_ratio=1 if i<=90 else (.5 if i<=105 else 0); paid=round(total*pay_ratio,2)
    paystatus='Paid' if paid>=total else ('Partial' if paid>0 else 'Outstanding')
    sales.append([sid,dt.strftime('%Y-%m-%d'),c['Customer ID'],c['Customer Name'],'Demo Sales Executive',subtotal,disc,0,total,paystatus,'Delivered' if i<=95 else 'Pending','Completed'])
    items.append([f'SLITEM-{i:06d}',sid,p['Product ID'],p['Product Name'],qty,price,disc,total])
    stock[p['Product ID']]=max(0,stock[p['Product ID']]-qty)
    invoices.append([iid,iid,dt.strftime('%Y-%m-%d'),(dt+timedelta(days=30)).strftime('%Y-%m-%d'),sid,c['Customer ID'],c['Customer Name'],subtotal,disc,0,total,paid,round(total-paid,2),paystatus,'Issued','Demo Administrator'])
    if paid:
        payments.append([f'PAY-{payno:06d}',(dt+timedelta(days=random.randint(0,5))).strftime('%Y-%m-%d'),iid,c['Customer ID'],c['Customer Name'],paid,random.choice(['Bank Transfer','Cash','POS']),f'DEMO-PAY-{payno:05d}','Demo Administrator','Demo payment']); payno+=1
    inv.append([f'STOCK-{n:06d}',dt.strftime('%Y-%m-%d'),p['Product ID'],p['Product Name'],'Stock Sold',qty,sid,c['Customer Name'],'Demo Administrator','Linked to demo sale']); n+=1
# write core tables
pd.DataFrame(sales,columns=['Sale ID','Date','Customer ID','Customer Name','Salesperson','Subtotal','Discount','Tax','Total Amount','Payment Status','Delivery Status','Status']).to_csv(base/'sales.csv',index=False)
pd.DataFrame(items,columns=['Sale Item ID','Sale ID','Product ID','Product Name','Quantity','Unit Price','Discount','Line Total']).to_csv(base/'sale_items.csv',index=False)
pd.DataFrame(invoices,columns=['Invoice ID','Invoice Number','Invoice Date','Due Date','Sale ID','Customer ID','Customer Name','Subtotal','Discount','Tax','Total Amount','Amount Paid','Balance Due','Payment Status','Invoice Status','Created By']).to_csv(base/'invoices.csv',index=False)
pd.DataFrame(payments,columns=['Payment ID','Payment Date','Invoice ID','Customer ID','Customer Name','Amount','Payment Method','Reference','Received By','Notes']).to_csv(base/'payments.csv',index=False)
pd.DataFrame(inv,columns=['Movement ID','Date','Product ID','Product Name','Movement Type','Quantity','Reference','Source/Destination','Recorded By','Notes']).to_csv(base/'inventory_movements.csv',index=False)
products['Current Stock']=products['Product ID'].map(stock).fillna(0).astype(int); products['Product Status']='Active'; products.to_csv(base/'products.csv',index=False)
# customer rollup
idf=pd.DataFrame(invoices,columns=['Invoice ID','Invoice Number','Invoice Date','Due Date','Sale ID','Customer ID','Customer Name','Subtotal','Discount','Tax','Total Amount','Amount Paid','Balance Due','Payment Status','Invoice Status','Created By'])
customers['Total Purchases']=customers['Customer ID'].map(idf.groupby('Customer ID')['Total Amount'].sum()).fillna(0).round(2)
customers['Outstanding Balance']=customers['Customer ID'].map(idf.groupby('Customer ID')['Balance Due'].sum()).fillna(0).round(2)
customers['Last Purchase']=today.strftime('%d %b %Y'); customers.to_csv(base/'customers.csv',index=False)
# trucks
trucks=[]; routes=['Kano Central','Sokoto North','Kaduna Route','Zaria Route','Katsina Route','Gusau Route','Birnin Kebbi Route','Jigawa Route']
for i in range(1,9): trucks.append([f'TRK-{i:06d}',f'KT-{random.randint(100,999)}-XY',f'DRV-{i:06d}',f'Demo Driver {i}',f'080{random.randint(10000000,99999999)}',random.choice([500,750,1000,1200]),routes[i-1],random.choice(['Available','On Delivery','Available','On Delivery'])])
pd.DataFrame(trucks,columns=['Truck ID','Registration Number','Driver ID','Driver Name','Driver Phone','Capacity','Assigned Route','Status']).to_csv(base/'trucks.csv',index=False)
# deliveries
sales_df=pd.DataFrame(sales,columns=['Sale ID','Date','Customer ID','Customer Name','Salesperson','Subtotal','Discount','Tax','Total Amount','Payment Status','Delivery Status','Status']); inv_df=pd.DataFrame(invoices,columns=['Invoice ID','Invoice Number','Invoice Date','Due Date','Sale ID','Customer ID','Customer Name','Subtotal','Discount','Tax','Total Amount','Amount Paid','Balance Due','Payment Status','Invoice Status','Created By'])
delivs=[]
for i in range(1,51):
    j=random.randrange(120); s=sales_df.iloc[j]; tr=trucks[random.randrange(8)]; status=random.choice(['Delivered','Delivered','Dispatched','In Transit','Pending']); dt=datetime.strptime(s['Date'],'%Y-%m-%d')
    delivs.append([f'DEL-2026-{i:06d}',s['Date'],tr[0],tr[1],tr[2],tr[3],s['Customer ID'],s['Customer Name'],s['Sale ID'],inv_df.iloc[j]['Invoice ID'],f'Demo Distribution Area {random.randint(1,25)}',tr[6],status,dt.strftime('%Y-%m-%d 08:30:00'),(dt+timedelta(hours=6)).strftime('%Y-%m-%d 14:30:00') if status=='Delivered' else '', 'Demo wholesale delivery'])
pd.DataFrame(delivs,columns=['Delivery ID','Delivery Date','Truck ID','Registration Number','Driver ID','Driver Name','Customer ID','Customer Name','Sale ID','Invoice ID','Delivery Address','Route','Status','Dispatch Time','Delivery Time','Notes']).to_csv(base/'deliveries.csv',index=False)
# expenditures + approvals
exp=[]; appr=[]
for i in range(1,21):
    eid=f'EXP-2026-{i:06d}'; status=random.choice(['Approved','Approved','Pending Approval','Completed','Rejected']); req=random.randint(50,400)*1000; approved=req if status in ['Approved','Completed'] else 0; paid=approved if status=='Completed' else 0
    ast='Approved' if status in ['Approved','Completed'] else ('Rejected' if status=='Rejected' else 'Pending Approval'); ad='Demo Manager' if ast=='Approved' else ''; date=(today-timedelta(days=random.randint(0,20))).strftime('%Y-%m-%d');
    exp.append([eid,eid,date,random.choice(['Logistics','Warehouse','Sales','Administration']),'Demo Administrator',random.choice(['Fuel','Vehicle Maintenance','Warehouse Expenses','Utilities','Office Supplies','Logistics']),f'Demo expenditure request {eid}',req,approved,paid,'Paid' if paid else 'Unpaid',ast,ad,today.strftime('%Y-%m-%d %H:%M:%S') if ad else '',today.strftime('%Y-%m-%d %H:%M:%S') if paid else '','Bank Transfer' if paid else '',f'DEMO-EXP-{i:05d}' if paid else '','','Demo expenditure'])
    appr.append([f'APR-{i:06d}',eid,'Expenditure','Demo Administrator','Administration',date,f'Demo expenditure request {eid}',req,0,'Normal',ast,ad,today.strftime('%Y-%m-%d %H:%M:%S') if ad else '','Approved' if ad else ('Rejected' if ast=='Rejected' else ''),'Demo approval workflow','',''])
# 10 stock approvals, 6 pending
for j in range(1,11):
    p=products.iloc[j-1]; status='Pending Approval' if j<=6 else ('Approved' if j<=8 else 'Completed'); ad='Demo Manager' if status in ['Approved','Completed'] else ''
    appr.append([f'APR-{20+j:06d}',f'REQ-2026-{j:06d}','Stock Request','Demo Warehouse Officer','Sales / Distribution',today.strftime('%Y-%m-%d %H:%M:%S'),f'{p["Product Name"]} — demo wholesale replenishment',0,random.randint(20,120),'Urgent' if j<=3 else 'Normal',status,ad,today.strftime('%Y-%m-%d %H:%M:%S') if ad else '','Approved' if ad else '','Demo warehouse approval' if ad else '',p['Product ID'],p['Product Name']])
pd.DataFrame(exp,columns=['Expenditure ID','Request ID','Date','Department','Requester','Expense Category','Description','Amount Requested','Amount Approved','Amount Paid','Payment Status','Approval Status','Approver','Approval Date','Payment Date','Payment Method','Payment Reference','Supporting Document','Notes']).to_csv(base/'expenditures.csv',index=False)
pd.DataFrame(appr,columns=['Approval ID','Request ID','Request Type','Requester','Department','Request Date','Description','Amount','Quantity','Priority','Status','Approver','Decision Date','Decision','Comment','Product ID','Product Name']).to_csv(base/'approvals.csv',index=False)
# audit
acts=[('SALE','Sale created'),('INVOICE','Invoice generated'),('PAYMENT','Payment recorded'),('STOCK','Inventory updated'),('DELIVERY','Delivery dispatched'),('APPROVAL','Request approved'),('EXPENDITURE','Expenditure submitted')]
audit=[]
for i in range(1,101): typ,msg=random.choice(acts); audit.append([f'AUD-{i:06d}',(today-timedelta(hours=random.randint(0,240))).strftime('%Y-%m-%d %H:%M:%S'),'Demo Administrator',typ,f'{msg} — DEMO transaction {i}',f'DEMO-{i:06d}'])
pd.DataFrame(audit,columns=['Audit ID','Timestamp','User','Action','Description','Reference ID']).to_csv(base/'audit_log.csv',index=False)
print('Sales:',len(sales),'Total:',round(sum(x[8] for x in sales),2))
print('Payments:',len(payments),'Total:',round(sum(x[5] for x in payments),2))
print('Outstanding:',round(sum(x[12] for x in invoices),2))
print('Stock units:',int(products['Current Stock'].sum()))
print('Trucks:',len(trucks),'Deliveries:',len(delivs),'Pending approvals:',sum(x[10]=='Pending Approval' for x in appr))
