def create_doc(model_wrapper, text):
    return model_wrapper.run(_do_create_doc, text)


def _do_create_doc(model, text):
    return model(text)
