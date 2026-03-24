# Stopping condition defaults
MAX_RUNTIME_SECONDS = 600  # 10 minutes hard cap
CONVERGENCE_PATIENCE = 1000  # generations without improvement
CONVERGENCE_THRESHOLD = 0.0  # minimum absolute improvement in distance units

# Window
WIDTH, HEIGHT = 800, 400
PADDING = 20

# Colors
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)  # regular delivery nodes
ORANGE = (255, 140, 0)  # critical delivery nodes
GREEN = (0, 255, 0)  # depot
VEHICLE_COLORS = [
    (0, 0, 255),  # blue
    (0, 180, 0),  # green
    (180, 0, 180),  # purple
    (0, 180, 180),  # cyan
    (180, 0, 0),  # dark red
    (100, 100, 255),  # light blue
    (255, 200, 0),  # yellow
    (255, 100, 180),  # pink
]

# Display
NODE_RADIUS = 10
FPS = 30
PLOT_X_OFFSET = 400

# GA
POPULATION_SIZE = 100
MUTATION_PROBABILITY = 0.5
CRITICAL_PRIORITY_WEIGHT = 2.0
