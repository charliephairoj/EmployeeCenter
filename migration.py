
""" Migrate to New Database.

    This migration file helps to migrate the databse from the old system to the new system.
    Both Systems are Postgresql, but the tablenames are different because the old system used
    php and the new system uses python via Django ORM. 

    The migration are accomplished by selecting all the rows from the old database, and inserting 
    into the new database if the id does not exists. After all the rows are updated because these
    tables are not yet used by the new system. In the future the system will be comparing timestamps
    to see which to update and which not to update"""
    
import psycopg2
import json

new_db_conn = psycopg2.connect(host='54.251.38.26', user='postgres', password='Har6401Vard88')
old_db_conn = psycopg2.connect(host='54.251.62.47', user='postgres', password='Har6401Vard88')
cur1 = old_db_conn.cursor()
cur2 = new_db_conn.cursor()


def prepare_upsert(table, *args):
    
    query1 = "WITH upsert AS(UPDATE %s SET " %table
    query2 = "INSERT INTO %s(" % table
    query3 = "SELECT "
    for key, arg in enumerate(args):
        #build update statement
        if key<len(args)-1:
            #Check not id for upsert
            if arg != "id":
                query1 += "%s = %%(%s)s, " %(arg, arg)
            #Adds comma to separate
            query2 += "%s, " % arg
            query3 += "%%(%s)s, " % arg
        #add returning
        if key == len(args)-1:
            query1 += "%s = %%(%s)s" % (arg, arg)
            query1 += " WHERE id = %(id)s RETURNING id) "
            query2 += "%s)" % arg
            query3 += "%%(%s)s WHERE NOT EXISTS (SELECT 1 FROM upsert)" % arg
        #build insert statement
            
            query = query1 + query2 + query3
            
            def upsert(arg_dict):
                
                print "ID: %s" % arg_dict['id']
                cur2.execute(query, arg_dict)
                print cur2.statusmessage
            
            return upsert

def update_contacts():
    print "Updating Contacts"
    #Get all configurations
    query1 = """SELECT customer_id, name, telephone, fax
                FROM customers 
                ORDER BY customer_id DESC"""
    cur1.execute(query1)
    #Create query for upsert at new db
    upsert = prepare_upsert("contacts_contact", "id", "name", "telephone", 'fax')
    #Fetch data and iterate
    rows = cur1.fetchall()
    for row in rows:
        #extract data and organize
        data = {'id':row[0],
                'name':row[1],
                'telephone':row[2],
                'fax':row[3]}
        #upsert
        upsert(data)
        
def update_contact_addresses():
    print "Updating Contact Addresses"
    #Get all configurations
    query1 = """SELECT address_id, address, city, territory, country, zipcode, customer_id
                FROM customer_addresses
                ORDER BY address_id DESC"""
    cur1.execute(query1)
    #Create query for upsert at new db
    upsert = prepare_upsert("contacts_address", "id", "address1", "city", 'territory', 'country',
                            'zipcode', 'contact_id')
    #Fetch data and iterate
    rows = cur1.fetchall()
    for row in rows:
        #extract data and organize
        data = {'id':row[0],
                'address1':row[1],
                'city':row[2],
                'territory':row[3],
                'country':row[4],
                'zipcode':row[5],
                'contact_id':row[6]}
        #upsert
        upsert(data)
            
def update_models():
    print "Updating Models"
    #Get all configurations
    query1 = """SELECT model_id, model, name, company 
                FROM models 
                ORDER BY model_id DESC"""
    cur1.execute(query1)
    
    #Create query for upsert at new db
    upsert = prepare_upsert("products_model", "id", "name", "model", "collection")
    
    rows = cur1.fetchall()
    for row in rows:
        #extract data and organize
        data = {'id':row[0],
                'model':row[1],
                'name':row[2],
                'collection':row[3]}
        
        upsert(data)
       



def update_model_images():
    
    print "Updating Model Images"
    #Get all configurations
    query1 = """SELECT model_image_id, model_id, link, file_size, image_order
                FROM model_images 
                ORDER BY model_image_id DESC"""
    cur1.execute(query1)
    #Create query for upsert at new db
    upsert = prepare_upsert('products_modelimage','id', 'model_id', 'url', 'file_size', 'image_order')
    
    #Fetch configurtion and iterate
    rows = cur1.fetchall()
    for row in rows:
        #extract data and organize
        data = {'id':row[0],
                'model_id':row[1],
                'url':row[2],
                'file_size':row[3],
                'image_order':row[4]}
        
        upsert(data)
        
        
        
def update_configurations():
    
    print "Updating Configurations"
    #Get all configurations
    query1 = """SELECT configuration_id, configuration 
                FROM configurations 
                ORDER BY configuration_id DESC"""
    cur1.execute(query1)
    #Create query for upsert at new db
    upsert = prepare_upsert('products_configuration','id', 'configuration')
   
    #Fetch configurtion and iterate
    rows = cur1.fetchall()
    for row in rows:
        #extract data and organize
        data = {'id':row[0],
                'configuration':row[1]}
        
        upsert(data)
        
#Update Upholstery     
def update_upholstery():
    
    
    print "Updating Upholstery"
    #Get all products
    query1 = """SELECT product_id, manufacture_price, wholesale_price, retail_price, width, 
        depth, height, configuration_id, model_id FROM products ORDER BY product_id DESC"""
    cur1.execute(query1)
    #query for product table
    upsert1 = prepare_upsert('products_product', 'id', 'manufacture_price', 'wholesale_price', 
                             'retail_price', 'width', 'depth','height', 'type')
    
    #query for upholstery table
    query3 = """WITH upsert AS
            (UPDATE products_upholstery SET configuration_id = %(configuration_id)s, model_id = %(model_id)s 
            WHERE product_ptr_id = %(id)s 
            RETURNING product_ptr_id)
            INSERT INTO products_upholstery(product_ptr_id, configuration_id, model_id) 
            SELECT %(id)s, 
                %(configuration_id)s, %(model_id)s
            WHERE NOT EXISTS (SELECT 1 FROM upsert)"""
    #iterate and upsert data
    rows = cur1.fetchall()
    for row in rows:
        #extract and organize data
        data = {'id':row[0],
                'manufacture_price':row[1],
                'wholesale_price':row[2],
                'retail_price':row[3],
                'width':row[4],
                'depth':row[5],
                'height':row[6],
                'configuration_id':row[7],
                'model_id':row[8],
                'type':'Upholstery'}
        #upsert and print message
        upsert1(data)
        cur2.execute(query3, data)
        print cur2.statusmessage

#Update Upholstery     
def update_upholstery_pillows():
    
    
    print "Updating Upholstery Pillows"
    #Get all products
    query1 = """SELECT product_pillow_id, product_id, type, quantity FROM product_pillows ORDER BY product_pillow_id DESC"""
    cur1.execute(query1)
    #query for product table
    upsert1 = prepare_upsert('products_pillow', 'id', 'product_id', 'type', 'quantity')
    
    #iterate and upsert data
    rows = cur1.fetchall()
    for row in rows:
        #extract and organize data
        data = {'id':row[0],
                'product_id':row[1],
                'type':row[2],
                'quantity':row[3]}
        #upsert and print message
        upsert1(data)
        
#update acknowledgements
def update_acks():
    
    """Gets the max id of the new db and compares with the old db and imports and newer ones"""
    
    print "Updating Acknowledgements"
    #Get all acks
    query1 = """SELECT acknowledgement_id, customer_id, employee_id, po_id, time_created, 
        delivery_date, fob, shipping, status, remarks FROM acknowledgements ORDER BY acknowledgement_id DESC"""
    cur1.execute(query1) 
    #construct query for upsert
    upsert = prepare_upsert('acknowledgements_acknowledgement', 'id', 'customer_id', 'employee_id',
                            'po_id', 'time_created', 'delivery_date', 'fob', 'shipping', 'status', 'remarks')
    
    #iterate over results
    rows = cur1.fetchall()
    for row in rows:
        #extract data and organize
        data = {'id':row[0],
               'customer_id':row[1],
               'employee_id':row[2],
               'po_id':row[3],
               'time_created':row[4],
               'delivery_date':row[5],
               'fob':row[6], 
               'shipping':row[7],
               'status':row[8],
               'remarks':row[9]}
        print data['id']
        #update or insert data
        upsert(data)
    #Reset id
    cur2.execute("""SELECT setval('acknowledgements_acknowledgement_acknowledgement_id_seq', (
                    SELECT MAX(id) FROM acknowledgements_acknowledgement))""")
  
def update_ack_items():
    
    print "Updating Acknowledgement Items"
    #query to get ack items    
    query1 = """SELECT acknowledgement_item_id, product_id, acknowledgement_id, quantity, fabric, 
    width, depth, height, custom, price, item_description, status FROM acknowledgement_items ORDER BY acknowledgement_item_id DESC"""
    cur1.execute(query1)
    
    #upsert query
    upsert = prepare_upsert("acknowledgements_item", 'id', 'product_id', 'acknowledgement_id', 'quantity',
                            'fabric', 'width', 'depth', 'height', 'is_custom_size', 'price', 'description', 'status')
             
    #Get data and iterate
    rows = cur1.fetchall()
    for row in rows:
        #extract and organize data
        data = {'id':row[0],
                'product_id':row[1],
                'acknowledgement_id':row[2],
                'quantity':row[3],
                'fabric':row[4],
                'width':row[5],
                'depth':row[6],
                'height':row[7],
                'is_custom_size':row[8],
                'price':row[9],
                'description':row[10],
                'status':row[11]}
        #update or insert data  
        upsert(data)
        
def update_ack_item_pillows():
    
    print "Updating Acknowledgement Item Pillows"
    #query to get ack items    
    query1 = """SELECT ap.acknowledgement_pillow_id, ap.acknowledgement_item_id, ap.fabric, ap.type, (
                SELECT quantity FROM product_pillows WHERE product_pillow_id = ap.PRODUCT_PILLOW_ID) AS quantity
                FROM acknowledgement_item_pillows AS ap"""
    cur1.execute(query1)
    
    #upsert query
    upsert = prepare_upsert("acknowledgements_pillow", 'id', 'item_id', 'fabric', 'type',
                            'quantity')
             
    #Get data and iterate
    rows = cur1.fetchall()
    for row in rows:
        #extract and organize data
        data = {'id':row[0],
                'item_id':row[1],
                'fabric':row[2],
                'type':row[3],
                'quantity':row[4]}
        #update or insert data  
        upsert(data)

def migrate():
    #update_contacts()
    #update_contact_addresses()
    #update_models()
    #update_model_images()
    #update_configurations()
    #update_upholstery()
    update_upholstery_pillows()
    #update_acks()
    #update_ack_items()
    #update_ack_item_pillows()


migrate()


new_db_conn.commit()
