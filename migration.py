
""" This migration file helps to migrate the databse from the old system to the new system.
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



        
def update_upholstery():
    
    
    print "Updating Upholstery"
    #Get all products
    query1 = """SELECT product_id, manufacture_price, wholesale_price, retail_price, width, 
        depth, height, configuration_id, model_id FROM products ORDER BY product_id DESC"""
    cur1.execute(query1)
    #query for product table
    query2 = """WITH upsert as 
            (UPDATE products_product SET manufacture_price = %(manufacture_price)s, wholesale_price = %(wholesale_price)s, 
                retail_price = %(retail_price)s, width = %(width)s, depth = %(depth)s, height = %(height)s 
            WHERE id = %(id)s 
            RETURNING id)
            INSERT INTO products_product(id, manufacture_price, wholesale_price, retail_price, width, depth, height, type)
            SELECT %(id)s, %(manufacture_price)s, %(wholesale_price)s, %(retail_price)s, %(width)s, %(depth)s, %(height)s,
                'Upholstery' 
            WHERE NOT EXISTS (SELECT 1 FROM upsert)"""
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
                'model_id':row[8]}
        #upsert and print message
        print "ID: %s" % data['id']
        cur2.execute(query2, data)
        print cur2.statusmessage
        cur2.execute(query3, data)
        print cur2.statusmessage

        
#update acknowledgements
def update_acks():
    
    """Gets the max id of the new db and compares with the old db and imports and newer ones"""
    
    print "Updating Acknowledgements"
    #Get all acks
    query1 = """SELECT acknowledgement_id, customer_id, employee_id, po_id, time_created, 
        delivery_date, fob, shipping, status, remarks FROM acknowledgements ORDER BY acknowledgement_id DESC"""
    cur1.execute(query1) 
    #construct query for upsert
    query2 = """WITH upsert AS (
            UPDATE acknowledgements_acknowledgement
            SET customer_id = %(customer_id)s, employee_id = %(employee_id)s, po_id = %(po_id)s,
                time_created = %(time_created)s, delivery_date = %(delivery_date)s, fob = %(fob)s, 
                shipping = %(shipping)s, status = %(status)s, remarks = %(remarks)s
            WHERE id = %(id)s RETURNING id)
            INSERT INTO acknowledgements_acknowledgement(id, customer_id, employee_id, po_id, time_created, delivery_date,
                fob, shipping, status, remarks)
            SELECT %(id)s, %(customer_id)s, %(employee_id)s, %(po_id)s,
                %(time_created)s, %(delivery_date)s, %(fob)s, %(shipping)s, %(status)s, %(remarks)s 
            WHERE NOT EXISTS (
            SELECT 1 FROM upsert)"""
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
        #Insert into new db
        cur2.execute(query2, data)
        print cur2.statusmessage
        
    
    #UPDATE THE SEQUENCE
    cur2.execute("SELECT setval('acknowledgements_acknowledgement_acknowledgement_id_seq', (SELECT MAX(id) FROM acknowledgements_acknowledgement), TRUE)")
    
    
    
    
def update_ack_items():
    
    print "Updating Acknowledgement Items"
    #query to get ack items    
    query1 = """SELECT acknowledgement_item_id, product_id, acknowledgement_id, quantity, fabric, 
    width, depth, height, custom, price, item_description, status FROM acknowledgement_items ORDER BY acknowledgement_item_id DESC"""
    cur1.execute(query1)
    
    #upsert query
    query2 = """WITH upsert AS (
                UPDATE acknowledgements_acknowledgementitem 
                SET product_id = %(product_id)s, acknowledgement_id = %(acknowledgement_id)s,
                    quantity = %(quantity)s, fabric = %(fabric)s, width = %(width)s, depth = %(depth)s,
                    height = %(height)s, is_custom_size = %(custom)s, price = %(price)s, description = %(description)s,
                    status = %(status)s
                WHERE id = %(id)s RETURNING id)
                INSERT INTO acknowledgements_acknowledgementitem(id, product_id, acknowledgement_id, quantity, fabric,
                    width, depth, height, is_custom_size, price, description, status)
                SELECT %(id)s, %(product_id)s, %(acknowledgement_id)s, %(quantity)s, %(fabric)s, %(width)s, %(depth)s, 
                    %(height)s, %(custom)s, %(price)s, %(description)s, %(status)s
                WHERE NOT EXISTS (SELECT 1 FROM upsert)"""            
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
                'custom':row[8],
                'price':row[9],
                'description':row[10],
                'status':row[11]}
        print "ID %s" %data["id"]
        #insert data
        cur2.execute(query2, data)
        print cur2.statusmessage


#update_upholstery()
update_acks()
#update_ack_items()



new_db_conn.commit()
