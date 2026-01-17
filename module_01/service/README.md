# Osteoporosis Risk Prediction Service

This is a FastAPI service for predicting osteoporosis risk using a trained machine learning model.

## Folder Structure

```
.
├── main.py                     # FastAPI application
├── model.pkl                   # Best performing model created in bone-density-analysis.ipynb
├── pre_process_pipeline.pkl    # Pre-processing pipeline created in bone-density-analysis.ipynb
├── requirements.txt            # Python dependencies
└── Dockerfile                  # Dockerfile for containerizing the service
```

## Running the service

Start the docker instance:

```
docker build -t op-risk-prediction-service . && docker run -p 8080:8080 op-risk-prediction-service
```

Access the service documentation at: http://localhost:8080. It contains all the necessary information that needs to be posted.

## Examples of cURL requests

This service contains only one endpoint: /predict

In this section we have some examples on how to interact with the API.

Notes:
- These commands use `| jq` to prettify the response. If you don't have it installed, then just remove it from the very last line.
- The payloads can be pasted in swagger if you prefer to use the API.


```
curl -s -X POST http://localhost:8080/predict \
-H "Content-Type: application/json" \
-d '{
  "Gender": 1,
  "Age": 68,
  "Height": 160,
  "Weight": 55,
  "BMI": 21.5,
  "L1_4": 0.85,
  "L1_4T": -1.8,
  "FN": 0.75,
  "FNT": -2.0,
  "TL": 0.7,
  "TLT": -2.1,
  "FBG": 5.6,
  "HDL_C": 1.1,
  "LDL_C": 3.5,
  "Ca": 2.3,
  "P": 1.0,
  "Mg": 0.9,
  "Fracture": 1,
  "Smoking": 0,
  "Drinking": 0
}' | jq
```

```
curl -s -X POST http://localhost:8080/predict \
-H "Content-Type: application/json" \
-d '{
  "Gender": 0,
  "Age": 45,
  "Height": 170,
  "Weight": 70,
  "BMI": 24.2,
  "L1_4": 1.1,
  "L1_4T": 0.3,
  "FN": 1.0,
  "FNT": 0.2,
  "TL": 0.95,
  "TLT": 0.1,
  "FBG": 5.2,
  "HDL_C": 1.4,
  "LDL_C": 2.8,
  "Ca": 2.35,
  "P": 1.1,
  "Mg": 1.0,
  "Fracture": 0,
  "Smoking": 0,
  "Drinking": 0
}' | jq
```