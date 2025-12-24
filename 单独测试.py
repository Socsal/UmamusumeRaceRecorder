import utils
import traceback
import os
import sys
import subprocess
import time
import cv2
import numpy as np
from PIL import Image
import pytesseract
from datetime import datetime
import argparse
import re


if __name__ == "__main__":
        devices = utils.list_connected_devices()
        print(devices)



