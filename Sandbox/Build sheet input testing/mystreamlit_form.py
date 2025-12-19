# Relevant imports
import pandas as pd
import streamlit as st
import datetime



st.title("IPX Order Form: BH Details")

""" Please fill in the details below for the BH order. """
""" """
Date = datetime.date.today()
st.write("Date: ", Date)

# Initial customer details:

customer = st.text_input("Customer Name")

project = st.text_input("Projecrt")

area_section = st.text_input("Area / Section")

completed_by = st.text_input("Completed By")



