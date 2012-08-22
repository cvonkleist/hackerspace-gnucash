# this reads all the customer IDs out of a GnuCash XML file

from xml.dom.minidom import parseString
from sys import argv
import gzip

file = gzip.open(argv[1],'r')
data = file.read()
file.close()

dom = parseString(data)
customerTags = dom.getElementsByTagName('gnc:GncCustomer')

for customerTag in customerTags:
  id = customerTag.getElementsByTagName('cust:id')[0].firstChild.nodeValue
  name = customerTag.getElementsByTagName('cust:name')[0].firstChild.nodeValue
  print id, "\t", name
