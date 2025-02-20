from typing import List, Tuple

from raw_keyboard_utils import distance


def get_segments(
    key_centers: List[Tuple[int, int]],
    x_coords: List[int],
    y_coords: List[int],
    ) -> List[List[Tuple[int, int]]]:
    """
    Isolates swipe sections corresponding to user targeting of individual keys.

    "SEGMENTS" algorithm from the "Modeling Gesture Typing Movements" paper 
    (https://doi.org/10.1080/07370024.2016.1215922).

    `segments[i]` corresponds to a portion of the swipe where 
    the user is targeting a `reduced_target_word[i]` character on the keyboard.
    Reduced target word is the target word with duplicate characters removed.

    Algorithm:
    1. Trim first/last two points from gesture
    2. Iterate over keys corresponding to target word characters. 
       For each key, collect points moving toward current key until closer to next key.
       When closer to next key, the segment is complete. Move to next key and repeat.
       Duplicate keys are skipped.
    3. Reattach trimmed points to first/last segments.

    Arguments:
    ----------
    key_centers: List[Tuple[int, int]]
        List of (x,y) coordinates of key centers 
        for each character in the target word.
    x_coords: List[int]
        X coordinates of gesture points.
    y_coords: List[int]
        Y coordinates of gesture points.

    Returns:
        List of segments, each being a list of (x,y) coordinate tuples.
    """
    if len(x_coords) != len(y_coords):
        raise ValueError("x_coords and y_coords must have equal length")
    
    if len(x_coords) < 4:
        raise ValueError("At least 4 points required for segmentation")

    segments = []

    # Trim first/last two points as per algorithm
    points = list(zip(x_coords[2:-2], y_coords[2:-2]))
    point_index = 0  # Track current position in points list

    # Collect segments (except for last segment)
    for current_key, next_key in zip(key_centers[:-1], key_centers[1:]):
        if current_key == next_key:
            continue  # Skip duplicate keys

        segment = []
        previous_dist_to_current = float('inf')
        current_x, current_y = current_key
        next_x, next_y = next_key

        # Collect points moving toward current key
        while point_index < len(points):
            px, py = points[point_index]
            dist_to_current = distance(px, py, current_x, current_y)
            dist_to_next = distance(px, py, next_x, next_y)

            if dist_to_current < previous_dist_to_current or dist_to_current < dist_to_next:
                segment.append(points[point_index])
                previous_dist_to_current = dist_to_current
                point_index += 1  # Move to next point
            else:
                break

        segments.append(segment)

    if not segments:  
        # The word had of only one unique charracter.
        # Example: 'ее' which is a way to type 'её'.
        segments.append(list(zip(x_coords, y_coords)))
        return segments

    # Reattach trimmed edge points
    first_two_points = list(zip(x_coords[:2], y_coords[:2]))
    segments[0] = first_two_points + segments[0]

    last_two_points = list(zip(x_coords[-2:], y_coords[-2:]))
    remaining_points = points[point_index:]  # Unprocessed points
    segments.append(remaining_points + last_two_points)

    return segments
