.. raw:: html

  <link href="_static/css/fontello.css" type="text/css" rel="stylesheet"/>

  <style type="text/css" media="screen">
    .the-icons {
        font-size: 20px;
        line-height: 28px;
    }
    .code-panel {
        background: white;
        box-shadow: 0px 0px 10px #ccc;
        margin-bottom: 10px;
    }
    .code-panel .header {
        padding: 10px;
        padding-top: 0px;
        min-height: 40px;
        border-top: 1px solid #ececec;
        background-color: #fff;
        text-align: left;
        display: block;
    }
    .code-panel .header .header-item {
        margin-top: 10px;
        margin-left: 5px;
        margin-right: 5px;
        vertical-align: middle;
        display: inline-block;
    }

    #result-div {
        float: right;
    }

    #cmdrun {
        padding-left: 25px;
        padding-right: 25px;
        background-color: #5bb75b;
        color: #ffffff;
        text-shadow: 0 -1px 0 rgba(0, 0, 0, 0.25);
        padding: 4px 12px;
        margin-bottom: 0;
        font-size: 14px;
        line-height: 20px;
        text-align: center;
        vertical-align: middle;
        cursor: pointer;
        border: 1px solid #cccccc;
        border-radius: 4px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.2), 0 1px 2px rgba(0,0,0,.05);
        font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;
    }
    .loader {
        border: 0.15em solid #f3f3f3; /* Light grey */
        border-top: 0.15em solid #3498db; /* Blue */
        border-radius: 50%;
        width: 1em;
        height: 1em;
        animation: spin 2s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    #cmdrun:disabled,
    #cmdrun[disabled]{
        border: 1px solid #999999;
        background-color: #cccccc;
        color: #666666;
    }

    #editor {
        position: relative;
        overflow: hidden;
        display: block;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        height: 320px;
    }
    #editor .ace_gutter > .ace_layer{
        background-color: white;
        width: 20px;
    }
    #consoleLog {
        position: relative;
        top: 0;
        bottom: 0;
        left: 0;
        height: 120px;
    }
    #editorContainer {
        border-top: 2px solid #ececec;
        padding-top: 5px;
        border-bottom: 2px solid #ececec;
    }

    #logContainer {
        margin-top: 5px;
    }

  </style>

PyGears LIVE! 
=============

Proba

.. raw:: html

    <div class="code-panel">
        <div class="header">
            <button id="cmdrun" class="header-item" onClick="javascript:runScript()"><i class="icon-cog-alt"></i> Run!</button>
            <div id="result-div" class="btn-group header-item">
                <button type="button" id="btn-result-zip" disabled="disabled" title="Download all result files as an archive"><i class="the-icons icon-download"></i></button>
                <button type="button" id="btn-result-browse" disabled="disabled" title="Browse result files"><i class="the-icons icon-folder-open-1"></i></button>
                <button type="button" id="btn-result-wave" disabled="disabled" title="View waveform"><i class="the-icons icon-menu"></i></button>
            </div>
        </div>

        <div id="editorContainer">
            <div id="editor">from pygears.cookbook import rng
  from pygears.common import shred
  from pygears.cookbook.verif import drv
  from pygears.typing import Uint

  drv(t=Uint[4], seq=[10]) | rng | shred</div>
        </div>
        <div id="logContainer">
            <div id="consoleLog"></div>
        </div>
    </div>


.. raw:: html

    <script src="_static/ace/ace.js" type="text/javascript" charset="utf-8"></script>

    <script type="text/javascript">

      function download(url) {
          let a = document.createElement('a')
          a.href = url
          a.download = url.split('/').pop()
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
      }

      function open_new_tab(url) {
          let a = document.createElement('a')
          a.href = url
          a.target = "_blank"
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
      }

      function partial(fn /*, rest args */){
          return fn.bind.apply(fn, Array.apply(null, arguments).slice(1));
      }

      function runScript() {
          var xhttp = new XMLHttpRequest();
          xhttp.onreadystatechange = function() {
              if (this.readyState == 4) {
                  if (this.status != 200) {
                      document.getElementById("cmdrun").innerHTML = 'Run!';
                      document.getElementById("cmdrun").disabled = false;
                      consoleLog.session.insert({
                          row: consoleLog.session.getLength(),
                          column: 0
                      }, "Server error!\n")
                      return;
                  }

                  var jsonResponse = JSON.parse(xhttp.responseText);

                  document.getElementById("cmdrun").innerHTML = '<i class="icon-cog-alt"></i> Run!';
                  document.getElementById("btn-result-zip").onclick = download.bind(
                      null, `${serverName}/results/${jsonResponse['result_id']}/results.zip`);
                  document.getElementById("btn-result-browse").onclick = open_new_tab.bind(
                      null, `${serverName}/results/${jsonResponse['result_id']}/`);
                  document.getElementById("btn-result-wave").onclick = open_new_tab.bind(
                      null, `${serverName}/wavedrom/${jsonResponse['result_id']}/sim/pygears`);

                  document.getElementById("btn-result-zip").disabled = false
                  document.getElementById("btn-result-browse").disabled = false
                  document.getElementById("btn-result-wave").disabled = false
                  document.getElementById("cmdrun").disabled = false;

                  /* console.log(xhttp.responseText); */
                  /* console.log(serverName + jsonResponse['log']) */
                  fetch(serverName + jsonResponse['log'])
                        .then(function(response) {
                            return response.text().then(function(text) {
                                consoleLog.setValue(text, -1);
                            });
                        });
              } else if (this.readyState == 1)  {
                  consoleLog.session.insert({
                      row: consoleLog.session.getLength(),
                      column: 0
                  }, `Running script...\n`)
              }
          };

          document.getElementById("btn-result-zip").disabled = true
          document.getElementById("btn-result-browse").disabled = true
          document.getElementById("btn-result-wave").disabled = true
          document.getElementById("cmdrun").disabled = true;

          document.getElementById("cmdrun").innerHTML =
              '<div style="margin:1px 7px 1px 6px" class="loader"></div>';

          consoleLog.setValue("Uploading script...\n", -1);

          xhttp.open("POST", `${serverName}/run`, true);
          xhttp.setRequestHeader("Content-Type", "application/json");
          xhttp.send(JSON.stringify({"script": editor.getValue()}));

          console.log("Script run");
      }

      /* var serverName = "http://127.0.0.1:5000"; */
      /* var serverName = "http://167.86.106.32:5000"; */
      var serverName = "http://167.86.106.32";

      document.getElementById("btn-result-zip").disabled = true
      document.getElementById("btn-result-browse").disabled = true
      document.getElementById("btn-result-wave").disabled = true
      document.getElementById("cmdrun").disabled = false;

      var editor = ace.edit("editor");
      /* editor.setTheme("ace/theme/chrome"); */
      editor.session.setMode("ace/mode/python");
      editor.setOption("showPrintMargin", false)
      editor.setOption("fontSize", 14)

      var consoleLog = ace.edit("consoleLog");
      /* editor.setTheme("ace/theme/chrome"); */
      consoleLog.session.setMode("ace/mode/text");
      consoleLog.setReadOnly(true);
      consoleLog.setOption('showLineNumbers', false);
      consoleLog.setOption('showGutter', false);
      consoleLog.setOption('highlightActiveLine', false);
      consoleLog.setOption("showPrintMargin", false)
      consoleLog.setOption("fontSize", 14)

    </script>
