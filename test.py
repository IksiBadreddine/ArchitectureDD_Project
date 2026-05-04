import pandas as pd
import numpy as np
from datetime import datetime
import os

INPUT_FILE = "silver_voitures_20260504_015638.csv" 

df = pd.read_csv(INPUT_FILE)

print(df.isnull().sum())