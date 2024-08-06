import os
import glob
import math
from datetime import datetime
from lxml import etree as ET

# Download path for FlightAware KML files.
srcDir = r'INSERT DESTINATION DIRECTORY HERE'

# Returns an array containing the texts of all the specified child nodes of root.
def getAll(root, node):
    return [_.text for _ in root.iterfind('.//' + node, namespaces=root.nsmap)]

# Calculates the groundspeed given two lat/long coordinates and associated start/end datetimes.
# TODO: Account for altitude differences.
def calcSpeed(fm, to, start, end):
    dx = math.hypot(*[b - a for a, b in zip(fm, to)]) * 60.0  # nautical miles
    dt = (end - start).total_seconds() / 3600.0  # hours
    return round(dx / dt) if dt else 0

# Converts a KML track log exported from flightaware.com to G1000 CSV format.
def export(kml):
    try:
        # Skip if already exported
        base = os.path.splitext(kml)[0]
        fileName = base + '.csv'
        if os.path.exists(fileName):
            print(f"File {fileName} already exists. Skipping.")
            return

        print('Exporting ' + fileName)

        # G1000 header, format, and trailing commas for data we do not set.
        hdr = '  Lcl Date, Lcl Time, UTCOfst, AtvWpt,     Latitude,    Longitude,    AltB, BaroA,  AltMSL,   OAT,    IAS, GndSpd,    VSpd,  Pitch,   Roll,  LatAc, NormAc,   HDG,   TRK, volt1,  FQtyL,  FQtyR, E1 FFlow, E1 FPres, E1 OilT, E1 OilP, E1 MAP, E1 RPM, E1 CHT1, E1 CHT2, E1 CHT3, E1 CHT4, E1 EGT1, E1 EGT2, E1 EGT3, E1 EGT4,  AltGPS, TAS, HSIS,    CRS,   NAV1,   NAV2,    COM1,    COM2,   HCDI,   VCDI, WndSpd, WndDr, WptDst, WptBrg, MagVar, AfcsOn, RollM, PitchM, RollC, PichC, VSpdG, GPSfix,  HAL,   VAL, HPLwas, HPLfd, VPLwas'
        fmt = '{date}, {time},   00:00,       , {lat: >12}, {lng: >12},        ,      , {alt: >7},      ,       , {gspd: >6}'
        tail = ',        ,       ,       ,       ,       ,      ,      ,      ,       ,       ,         ,         ,        ,        ,       ,       ,        ,        ,        ,        ,        ,        ,        ,        ,        ,    ,     ,       ,       ,       ,        ,        ,       ,       ,       ,      ,       ,       ,       ,       ,      ,       ,      ,      ,      ,       ,     ,      ,       ,      ,       '

        tree = ET.parse(kml)
        root = tree.getroot()

        # Collect all the timestamps and breadcrumbs.
        whens = getAll(root, 'when')
        coords = getAll(root, 'gx:coord')
        
        if not whens or not coords:
            print(f"No valid data found in {kml}. Skipping.")
            return
        
        # Export the CSV header.
        csv = [hdr]

        # Export the CSV data.
        fm = None
        start = None
        for when, coord in zip(whens, coords):
            # Parse data (e.g. 2022-06-09T15:42:34.310Z)
            date, time = when.split('T')
            time = time.rstrip('Z')  # strip Z

            # Handle milliseconds
            if '.' in time:
                time, ms = time.split('.')
                ms = int(ms)
            else:
                ms = 0

            lng, lat, alt = coord.split(' ')

            # Calculate ground speed.
            to = (float(lat), float(lng))
            end = datetime.strptime(date + ' ' + time, '%Y-%m-%d %H:%M:%S')
            end = end.replace(microsecond=ms * 1000)  # Add milliseconds
            gspd = calcSpeed(fm, to, start, end) if fm and start else 0
            fm = to
            start = end

            # FlightAware KML altitude is in meters, while G1000 wants feet.
            alt = round(float(alt) * 3.28084)

            # Append data with trailing commas for unset values.
            csv.append(fmt.format(date=date, time=time, lat=lat, lng=lng, alt=alt, gspd=gspd) + tail)

        # Write file to disk.
        with open(fileName, 'w') as f:
            f.writelines('\n'.join(csv))
    except Exception as e:
        print(f"Error processing {kml}: {e}")

# Convert all files in source directory.    
files = glob.glob(os.path.join(srcDir, '*.kml'))
if not files:
    print(f"No KML files found in {srcDir}.")
else:
    for fileName in files:
        export(fileName)
