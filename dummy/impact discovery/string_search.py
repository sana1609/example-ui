from sql_metadata import Parser

tables = Parser("SELECT * FROM Customers WHERE age = ( SELECT MIN(age) FROM Students);").tables
tables2 = Parser("DELETE FROM neworder WHERE advance_amount< (SELECT MAX(advance_amount) FROM orders);").tables
tables3 = Parser("SELECT customer_id, first_name FROM Customers WHERE customer_id IN ( SELECT customer_id FROM Orders);").tables
tables4 = Parser("SELECT DISTINCT Customers.customer_id, Customers.first_name FROM Customers INNER JOIN Orders ON Customers.customer_id = Orders.customer_id ORDER BY Customers.customer_id;").tables
try:

    tables5 = Parser("select 'from product'").tables
except ValueError as e :
    print(e)
# print( {"error encountered": "Query is not properly build"})
# tables6 = Parser("SELECT C.customer_id, C.first_name, O.amount, S.status FROM Customers AS C INNER JOIN Orders AS O ON C.customer_id = O.customer INNER JOIN Shipping AS S ON C.customer_id = S.customer_id;").tables
# tables7 = Parser("CREATE TABLE Companies (id int, name varchar(50), address text, email varchar(50), phone varchar(10));").tables
# tables8 = Parser("CREATE TABLE USACustomers AS ( SELECT * FROM Customers WHERE country = 'USA');").tables


