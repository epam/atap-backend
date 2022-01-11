import cv2
import numpy as np


conf_threshold = 0.5
nms_threshold = 0.4


def get_output_layers(net):
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    return output_layers


def object_detection(image_name):
    image = cv2.imread(image_name)
    if image is None:
        return []
    width = image.shape[1]
    height = image.shape[0]
    scale = 0.00392

    classes = None
    path = '/models/yolo/'
    with open(f'{path}yolov3.txt', 'r') as f:
        classes = [line.strip() for line in f.readlines()]
    net = cv2.dnn.readNet(f'{path}yolov3.weights',
                          'framework/tests/images/yolo/yolov3.cfg')
    blob = cv2.dnn.blobFromImage(image, scale, (416, 416), (0, 0, 0), True, crop=False)

    net.setInput(blob)

    outs = net.forward(get_output_layers(net))

    class_ids = []
    confidences = []
    boxes = []

    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                class_ids.append(class_id)
                confidences.append(float(confidence))
                boxes.append([center_x - w / 2, center_y - h / 2, w, h])

    return [str(classes[class_ids[i[0]]]) for i in cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)]