from typing import Callable

script_onID_creator = """
    var script = arguments[0];
    var id = arguments[1];
    var customScriptID = document.body.appendChild(document.createElement('script'));
    var encodedID;

    String.prototype.hexEncode = function() {
        var hex, i;

        var result = "";
        for (i=0; i<this.length; i++) {
            hex = this.charCodeAt(i).toString(16);
            result += ("000"+hex).slice(-4);
        }

        return result;
    };

    function randomId(arrInt) {
        const uint32 = window.crypto.getRandomValues(new Uint32Array(arrInt))[0];
        return uint32.toString(16);
    }

    encodedID = ("" + id.hexEncode()).split("");
    encodedID.forEach((n, i, arr) => { arr[i] = parseInt(n); });
    encodedID = randomId(encodedID);
    customScriptID.setAttribute("id", encodedID);
    customScriptID.innerText = `${arguments[0]}`;

    return encodedID;
"""


def eval_js(
    *script_names, recorder: Callable, evaluator: Callable, eval_args: list = [], eval_confirm_async=None
):
    """
    Wrapper on execute_script
    Args:
        recorder (function): class function that returns js representation of registered script, gets by ID
        evaluator (function): class function to execute script instead of builtin
        eval_args (list, optional): optional execute script arguments. Defaults to [].
        eval_confirm_async: map object with async_execute_script to implement timeout and check all done. Defaults to None.
    """
    _ = [evaluator(*eval_args, script=recorder(name)) for name in script_names]
    if eval_confirm_async:
        eval_confirm_async = dict(zip(["after timeout script output"], eval_confirm_async))


class CompoundJavascriptEngager:
    def __init__(
        self,
        webdriver_instance=None,
        activity=None,
        element_locator=None,
        scripts=[],
        script_names=[],
        timeout=10,
        **kwargs,
    ):
        if not hasattr(self, "driver"):
            self.driver = webdriver_instance
            self.activity = activity
            self.locator = element_locator
        self.timeout = timeout
        self.script_names = script_names
        self.scripts = scripts
        self.onpage_scripts = dict()
        self.driver.set_script_timeout(self.timeout)
        super().__init__(**kwargs)

    def register_js(self, registar: Callable, vault: dict):
        """
        Register imported scripts within webpage <script/>.
        Scripts have unique IDs, but will be addressed by sensible names'

        Args:
            registar (function): class function to register script
            vault (dict): mapper name: script.id
        """
        vault = dict.fromkeys(map(registar, self.scripts, self.script_names))

    def execute_script_eval(self, *args, script="return false;"):
        """Modification of execute_script"""
        pos = len(args)
        args = args + (script,)
        return self.driver.execute_script(f"eval(arguments[{pos}]); return false;", *args)

    def register_script(self, script, name):
        """Add a unique custom js at body bottom of current webpage"""
        self.onpage_scripts[name] = self.driver.execute_script(script_onID_creator, script, name)
        self.driver.find_element_by_id(self.onpage_scripts[name])

    def fetch_script_source(self, name):
        """Execute your compound js, registered at body bottom before"""
        script_id = self.onpage_scripts[name]
        return self.driver.find_element_by_id(script_id).get_attribute("innerHTML")
