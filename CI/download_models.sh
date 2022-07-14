cd /models

if [ ! -f GoogleNews.bin ]; then
  echo "ERROR: Google News work2vec model not found!"
fi

if [ ! -d $NLTK_DATA ]; then
  echo "nltk_data not found, downloading"
  python3 -m nltk.downloader -d $NLTK_DATA all
fi

if [ ! -d /models/spacy ]; then
  echo "SpaCy model not found, downloading"
  mkdir /models/spacy
  cd /models/spacy
  wget -q -c "https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-2.2.0/en_core_web_lg-2.2.0.tar.gz" --output-document=en_core_web_lg.tar.gz
  echo "Unpacking..."
  tar xf en_core_web_lg.tar.gz
  mv en_core_web_lg-2.2.0 en_core_web_lg
  rm en_core_web_lg.tar.gz
fi

if [ ! -d /models/yolo ]; then
  echo "YOLO model not found, downloading"
  mkdir /models/yolo
  cd /models/yolo
  wget -q -c "https://pjreddie.com/media/files/yolov3.weights"
fi
