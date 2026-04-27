import asyncio
import websockets
import json
import psycopg2
from datetime import datetime
from config import *

# Database connection
conn = psycopg2.connect(
    dbname="varmdoe_geodata",
    user="postgres",
    password=DB_PASSWORD,
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Create table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS vessels (
        id SERIAL PRIMARY KEY,
        mmsi VARCHAR(20),
        vessel_name VARCHAR(100),
        lat DOUBLE PRECISION,
        lon DOUBLE PRECISION,
        speed DOUBLE PRECISION,
        heading DOUBLE PRECISION,
        timestamp TIMESTAMP,
        geom GEOMETRY(Point, 4326)
    );
""")
conn.commit()

# Värmdö bounding box
BOUNDING_BOX = [
    [58.8, 18.0],  # bottom left
    [59.5, 19.2]   # top right
]

async def stream_ais():
    url = "wss://stream.aisstream.io/v0/stream"
    
    subscribe_message = {
        "APIKey": API_KEY,
        "BoundingBoxes": [BOUNDING_BOX],
        "FilterMessageTypes": ["PositionReport"]
    }

    print("Connecting to AIS stream...")
    
    async with websockets.connect(url) as websocket:
        await websocket.send(json.dumps(subscribe_message))
        print("Connected. Receiving vessel data...")
        
        async for message in websocket:
            data = json.loads(message)
            
            if "Message" in data:
                msg = data["Message"].get("PositionReport", {})
                meta = data.get("MetaData", {})
                
                mmsi = str(meta.get("MMSI", ""))
                name = meta.get("ShipName", "Unknown").strip()
                lat = msg.get("Latitude", 0)
                lon = msg.get("Longitude", 0)
                speed = msg.get("Sog", 0)
                heading = msg.get("TrueHeading", 0)
                timestamp = datetime.utcnow()

                if lat == 0 and lon == 0:
                    continue

                cur.execute("""
                    INSERT INTO vessels 
                    (mmsi, vessel_name, lat, lon, speed, heading, timestamp, geom)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                """, (mmsi, name, lat, lon, speed, heading, timestamp, lon, lat))
                conn.commit()
                
                print(f"Vessel: {name} | MMSI: {mmsi} | Position: {lat}, {lon} | Speed: {speed} knots")

asyncio.run(stream_ais())