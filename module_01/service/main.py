import logging
import pickle

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Osteoporosis Risk Prediction Service",
    version="1.0.0",
    description=(
        "Estimates the risk of osteoporosis based on patient data.<br><br>"
        "Intended to be used by medical professionals.<br><br>"
        "The final interpretation and diagnosis are the responsibility of the healthcare provider."
    )
)


@app.on_event("startup")
def startup_event():
    logger.info("API is starting...")

    logger.info("Loading model...")
    model = pickle.load(open("./model.pkl", "rb"))

    logger.info(f"Loaded model type: {type(model).__name__}")

    if hasattr(model, "get_params"):
        logger.info(f"Model params: {model.get_params()}")

    logger.info("Loading pre-processing pipeline...")
    pipeline = pickle.load(open("./pre_process_pipeline.pkl", "rb"))

    app.state.model = model
    app.state.pipeline = pipeline
    logger.info("API ready to accept requests.")


@app.get("/", include_in_schema=False)
def root():
    # Always redirect root to docs
    return RedirectResponse(url="/docs")


class PatientData(BaseModel):
    Gender: int
    Age: float
    Height: float
    Weight: float
    BMI: float
    L1_4: float
    L1_4T: float
    FN: float
    FNT: float
    TL: float
    TLT: float
    FBG: float
    HDL_C: float
    LDL_C: float
    Ca: float
    P: float
    Mg: float
    Fracture: int
    Smoking: int
    Drinking: int


class PredictionResponse(BaseModel):
    prediction: int
    risk_probability: float
    note: str = "Final interpretation and diagnosis are the responsibility of a healthcare professional."


@app.post("/predict", tags=["Prediction"])
def predict_risk(patient: PatientData) -> PredictionResponse:
    features = np.array([[
        patient.Gender,
        patient.Age,
        patient.Height,
        patient.Weight,
        patient.BMI,
        patient.L1_4,
        patient.L1_4T,
        patient.FN,
        patient.FNT,
        patient.TL,
        patient.TLT,
        patient.FBG,
        patient.HDL_C,
        patient.LDL_C,
        patient.Ca,
        patient.P,
        patient.Mg,
        patient.Fracture,
        patient.Smoking,
        patient.Drinking
    ]])

    features_scaled = app.state.pipeline.transform(features)

    pred = int(app.state.model.predict(features_scaled)[0])
    logger.info(f"Predicted risk: {pred}")

    # Probability of OP = 1 / class 1
    prob = app.state.model.predict_proba(features_scaled)[0][1]
    logger.info(f"Predicted risk probability: {prob:.4f}")

    return PredictionResponse(prediction=pred, risk_probability=prob)
