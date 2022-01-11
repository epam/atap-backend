import spacy
from threading import Lock
import billiard
import multiprocessing
from gensim.models.keyedvectors import KeyedVectors
import traceback
import logging
import os
import time
from queue import Empty

logger = logging.getLogger("framework.model_wrapper")

model_processes = []


def run_model(model_loader, input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue):
    logger.info("Loading the model...")
    try:
        model = model_loader()
    except Exception as e:
        logger.error("Failed to load model!")
        output_queue.put((e, "FAIL"))
        return

    logger.info("Loaded!")
    output_queue.put((None, "SUCCESS"))

    while os.getppid() != 1:
        try:
            # Timeout to re-check parent process status
            func_in, args, kwargs = input_queue.get(timeout=10)
            data_out = func_in(model, *args, **kwargs)
            output_queue.put((None, data_out))
        except Empty:
            pass
        except Exception as e:
            output_queue.put((e, traceback.format_exc()))


def model_unload_watcher(model_process):
    # When the parent process is terminated, the init process becomes the parent process
    while os.getppid() != 1:
        time.sleep(1)
    model_process.terminate()
    logger.info("Model process terminating - parent terminated")


class LockWrapper:
    def __init__(self, model_loader):
        self.lock = Lock()
        # cx = multiprocessing.get_context("fork")

        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.process = billiard.context.Process(target=run_model, args=(model_loader, self.input_queue, self.output_queue))
        self.process.daemon = True
        logger.info("Starting the model process")
        self.process.start()
        logger.info("Starting the model unload watcher")
        self.model_unload_watcher = billiard.context.Process(target=model_unload_watcher, args=(self.process,))
        self.model_unload_watcher.start()
        process_result = self.output_queue.get()
        if process_result[0] is None:
            logger.info("Model loaded ok, finishing task")
        else:
            logger.error("Exception while loading model!")
            raise process_result[0]

    def run(self, func, *args, **kwargs):
        if not self.process.is_alive():
            raise ValueError("Model process is dead, was the model accessed after unloading?")
        self.lock.acquire()
        try:
            self.input_queue.put((func, args, kwargs))
            result = self.output_queue.get()
            if result[0] is not None:
                print(result[1])
                raise result[0]
        finally:
            self.lock.release()
        return result[1]

    def unload(self):
        logger.info("Unloading model")
        self.process.terminate()
        self.model_unload_watcher.terminate()


def load_spacy_en_lg():
    return spacy.load("/models/spacy/en_core_web_lg/en_core_web_lg/en_core_web_lg-2.2.0")


def load_word2vec_googlenews():
    return KeyedVectors.load_word2vec_format('/models/GoogleNews.bin', binary=True)


MODEL_LOADERS = {
    "spacy_en_lg": load_spacy_en_lg,
    'word2vec_googlenews': load_word2vec_googlenews,
}


class NoSuchModelError(Exception):
    pass


def load(model_name):
    logger.info("LOADING MODEL")
    logger.info(model_name)
    if model_name not in MODEL_LOADERS:
        raise NoSuchModelError
    logger.info(f"Will load {model_name}")
    wrapper = LockWrapper(MODEL_LOADERS[model_name])
    model_processes.append(wrapper)
    return wrapper


def unload_all():
    global model_processes
    for model_id, wrapper in enumerate(model_processes):
        print(f"Cleaning up, unloading model {model_id+1}/{len(model_processes)}")
        wrapper.unload()
    model_processes = list()
