#!/usr/bin/env python

# insert_invoices.py
#
# Modified from original in 2012. Original license follows.
#
## Copyright (C) 2010 ParIT Worker Co-operative <transparency@parit.ca>
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, contact:
## Free Software Foundation           Voice:  +1-617-542-5942
## 51 Franklin Street, Fifth Floor    Fax:    +1-617-542-2652
## Boston, MA  02110-1301,  USA       gnu@gnu.org


# Opens a GnuCash book file and adds invoices to it for a set of
# customers (by their IDs). The user specifies a starting invoice ID which will
# be used for the first invoice, and each subsequent invoice creation will
# increment the previous invoice number by one.
#
# Usage:
#
# gnucash-env python insert_invoices.py \
#   <gnucash filename> <staring invoice number> <invoice title> \
#   <invoice amount> <customer id 1> [<customer id 2> ...]
#
# Example usage:
#
# gnucash-env python insert_invoices.py \
#   hackerspace.gnucash 1000 'Monthly dues' 40.00 000003 000006 ...
#
# argv[1] should be the path to an existing gnucash file/database. For a file,
# pass the pathname. For a database you can use these forms:
#
# mysql://user:password@host/dbname
# postgres://user:password@host[:port]/dbname (the port is optional)

from gnucash import Session, GUID, GncNumeric
from gnucash.gnucash_business import Customer, Invoice, Entry, BillTerm
from gnucash.gnucash_core_c import string_to_guid
from os.path import abspath
from sys import argv
from decimal import Decimal
import datetime


def gnc_numeric_from_decimal(decimal_value):
    sign, digits, exponent = decimal_value.as_tuple()

    # convert decimal digits to a fractional numerator
    # equivlent to
    # numerator = int(''.join(digits))
    # but without the wated conversion to string and back,
    # this is probably the same algorithm int() uses
    numerator = 0
    TEN = int(Decimal(0).radix()) # this is always 10
    numerator_place_value = 1
    # add each digit to the final value multiplied by the place value
    # from least significant to most sigificant
    for i in xrange(len(digits)-1,-1,-1):
        numerator += digits[i] * numerator_place_value
        numerator_place_value *= TEN

    if decimal_value.is_signed():
        numerator = -numerator

    # if the exponent is negative, we use it to set the denominator
    if exponent < 0 :
        denominator = TEN ** (-exponent)
    # if the exponent isn't negative, we bump up the numerator
    # and set the denominator to 1
    else:
        numerator *= TEN ** exponent
        denominator = 1

    return GncNumeric(numerator, denominator)


# command-line options
gnucash_filename = argv[1]
first_invoice_number = argv[2]
description = argv[3]
invoice_value = gnc_numeric_from_decimal(Decimal(argv[4]))
customer_ids = argv[5:]

#Check that the date is set correctly for a batch of invoices.
#Generally, the date should be set to the beginning of each month
#for the month of the billing period.

invoice_date = datetime.date(2012, 8, 1)

session = Session(gnucash_filename, is_new=False)
session.save() # this seems to make a difference in more complex cases

book = session.book
root_account = book.get_root_account()

commodity_table = book.get_table()
USD = commodity_table.lookup('CURRENCY', 'USD')

assets = root_account.lookup_by_name("Assets")
receivables = assets.lookup_by_name("Accounts Receivable")

# This assumes you have an income subaccount of the form "Income:Member Dues"
# The lookup fails if the parent account is specified.
# IE root_account.lookup_by_name("Income:Member Dues") does not work.

income = root_account.lookup_by_name("Member Dues")

# This is super hacky. The gnucash python api doesn't seem to make it possible
# to look up billing terms, so here we copy billing terms from an old invoice
# that had ones we like. if the invoice number ever goes away, this will stop
# working. :(
old_invoice = book.InvoiceLookupByID("000149")
terms = old_invoice.GetTerms()

# look up customer objects. do this before invoice insertion to ensure the ids
# are correct.
customers = []

for customer_id in customer_ids:
    customer = book.CustomerLookupByID(customer_id)
    assert(customer != None)
    assert(isinstance(customer, Customer))
    customers.append(customer)

# insert invoices
invoice_number = int(first_invoice_number)

for customer in customers:
    invoice = Invoice(book, str(invoice_number), USD, customer)
    invoice.SetTerms(terms)
    invoice_entry = Entry(book, invoice)
    
    invoice_entry.SetInvTaxIncluded(False)
    invoice_entry.SetDescription(description)
    invoice_entry.SetQuantity(GncNumeric(1))
    invoice_entry.SetInvAccount(income)
    invoice_entry.SetInvPrice(invoice_value)
    invoice_entry.SetDate(invoice_date)
    invoice_entry.SetDateEntered(invoice_date)

    invoice.PostToAccount(receivables, invoice_date,
	                  invoice_date+datetime.timedelta(days=15) ,description, True) #Set the due date 15 days later

    print "Created invoice number", invoice_number, "for customer", customer.GetName(), "(" + str(customer.GetID()) + ")"
    invoice_number += 1

session.save()
session.end()
print "Done."
