# Osteoporosis Risk Prediction

The goal of this project is to create a model that can provide osteoporosis risk predictions, to help healthcare 
professionals in their final decision.

## Folder Structure

```
.
├── analysis/
│   ├── bone-density-analysis.ipynb     # Analysis report
│   └── UA.csv                          # Dataset
│
├── models/                             # Final versions of the models 
│   ├── pre_process_pipeline.pkl
│   ├── logistic_regression.pkl
│   ├── knn.pkl
│   ├── decision_tree.pkl
│   └── random_forest.pkl
│
└── service/                            # REST API to host the model
    └── README.md
```