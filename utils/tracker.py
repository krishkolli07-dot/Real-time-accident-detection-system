import math

class VehicleTracker:
    def __init__(self):
        self.prev_positions = {}
        self.static_counter = {}

    def distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def update(self, vehicle_id, center, move_thresh=5, static_thresh=15):
        accident = False

        if vehicle_id in self.prev_positions:
            d = self.distance(center, self.prev_positions[vehicle_id])

            if d < move_thresh:
                self.static_counter[vehicle_id] = self.static_counter.get(vehicle_id, 0) + 1
            else:
                self.static_counter[vehicle_id] = 0

            if self.static_counter[vehicle_id] >= static_thresh:
                accident = True

        self.prev_positions[vehicle_id] = center
        return accident
