// Import d3.js, crossfilter.js and dc.js.
// import * as d3 from "./static/lib/d3.v3";
// import * as crossfilter from "./static/lib/crossfilter.js";
// import * as dc from "./static/lib/dc.js";

// Import base class.
import Stage from './Stage.js'
import FilterReduceOperator from "../operators/FilterReduceOperator.js";
import SurrogateModelOperator from "../operators/SurrogateModelOperator.js";
import DissonanceOperator from "../operators/DissonanceOperator.js";
import Utils from "../Utils.js";
import DissonanceDataset from "../data/DissonanceDataset.js";
import ModelDetailOperator from "../operators/ModelDetailOperator.js";

/**
 * Stage for prototype (2018-02).
 */
export default class PrototypeStage extends Stage
{
    /**
     *
     * @param name
     * @param target ID of container div.
     * @param datasets Dictionary of isnstance of dataset class.
     */
    constructor(name, target, datasets)
    {
        super(name, target, datasets);

        // Store splitter instance for bottom div.
        this._bottomSplitPane = null;

        // Construct operators.
        this.constructOperators()
    }

    /**
     * Construct all panels for this view.
     */
    constructOperators()
    {
        let scope = this;

        // Fetch (test) dataset for surrogate model first, then initialize panels.
        let surrModelJSON = fetch(
            "/get_surrogate_model_data?modeltype=tree&objs=r_nx,b_nx&depth=4",
            {
                headers: { "Content-Type": "application/json; charset=utf-8"},
                method: "GET"
            }
        ).then(res => res.json());

        let dissonanceDataJSON = fetch(
            "/get_sample_dissonance",
            {
                headers: { "Content-Type": "application/json; charset=utf-8"},
                method: "GET"
            }
        ).then(res => res.json());

        // Fetch data.
        Promise.all([surrModelJSON, dissonanceDataJSON])
            .then(function(values) {
                scope._datasets["surrogateModel"]   = values[0];
                // Compile DissonanceDataset.
                console.log("Compiling DissonanceDataset.");
                scope._datasets["dissonance"]       = new DissonanceDataset(
                    "Dissonance Dataset",
                    values[1],
                    {x: 20, y: 10},
                    scope._datasets["modelMetadata"],
                    "r_nx"
                );

                // For panels at bottom: Spawn container.
                let splitTopDiv = Utils.spawnChildDiv(scope._target, null, "split-top-container");
                // For panels at bottom: Spawn container. Used for surrogate and dissonance panel.
                let splitBottomDiv = Utils.spawnChildDiv(scope._target, null, "split-bottom-container");

                //---------------------------------------------------------
                // 1. Operator for hyperparameter and objective selection.
                // ---------------------------------------------------------

                scope._operators["FilterReduce"] = new FilterReduceOperator(
                    "FilterReduce:TSNE",
                    scope,
                    scope._datasets["modelMetadata"],
                    splitTopDiv.id,
                    splitBottomDiv.id
                );

                // ---------------------------------------------------------
                // 2. Operator for exploration of surrogate model (read-only).
                // ---------------------------------------------------------

                scope._operators["SurrogateModel"] = new SurrogateModelOperator(
                    "GlobalSurrogateModel:DecisionTree",
                    scope,
                    scope._datasets["surrogateModel"],
                    "Tree",
                    splitBottomDiv.id
                );

                // ---------------------------------------------------------
                // 3. Operator for exploration of inter-model disagreement.
                // ---------------------------------------------------------

                scope._operators["Dissonance"] = new DissonanceOperator(
                    "Dissonance:DecisionTree",
                    scope,
                    scope._datasets["dissonance"],
                    splitBottomDiv.id
                );

                // ---------------------------------------------------------
                // 4. Operator for model (+ sample) detail view.
                // ---------------------------------------------------------

                scope._operators["ModelDetail"] = new ModelDetailOperator(
                    "Detail:DRModel",
                    scope,
                    scope._datasets["modelMetadata"],
                    // Note that MD view is currently a modal, hence it doesn't matter which parent div is used.
                    scope._target
                );

                // ---------------------------------------------------------
                // 4. Initialize split panes.
                // ---------------------------------------------------------

                let surrTarget              = scope._operators["SurrogateModel"]._target;
                let dissTarget              = scope._operators["Dissonance"]._target;
                let embeddingsTableTarget   = scope._operators["FilterReduce"].tablePanel._target;

                // Horizontal split.
                $("#" + surrTarget).addClass("split split-horizontal");
                $("#" + dissTarget).addClass("split split-horizontal");
                $("#" + embeddingsTableTarget).addClass("split split-horizontal");
                scope._bottomSplitPane = Split(
                    ["#" + embeddingsTableTarget, "#" + surrTarget, "#" + dissTarget],
                    {
                        direction: "horizontal",
                        sizes: [2, 49, 49],
                        onDragEnd: function() {}
                    }
                );
                // scope._bottomSplitPane.collapse(0);

                // Vertical split.
                $("#" + splitTopDiv.id).addClass("split split-vertical");
                $("#" + splitBottomDiv.id).addClass("split split-vertical");
                Split(
                    ["#" + splitTopDiv.id, "#" + splitBottomDiv.id],
                    {
                        direction: "vertical",
                        sizes: [57, 43],
                        onDragEnd: function() {
                        }
                    }
                );

                // After split: Render (resize-sensitive) components.
                scope._operators["SurrogateModel"].render();
                scope._operators["Dissonance"].render();
                $("#" + embeddingsTableTarget + " .dataTables_scrollBody").css(
                    'height', ($("#" + splitBottomDiv.id).height() - 200) + "px"
                );

                // ---------------------------------------------------------
                // 5. Fade out splash screen, fade in stage.
                // ---------------------------------------------------------

                  $("#stage").fadeTo(2000, 1.0);
                  $("#splashscreen").fadeTo(1000, 0, function() {
                      $("#splashscreen").css("display", "none");
                  });

                  let now = new Date();
                  console.log("*** DROP *** Finished construction at " + now.getHours() + ":" + now.getMinutes() + ":" + now.getSeconds() + ".");
            });
    }

    /**
     * Toggles visiblity of embeddings overview table.
     * @param show
     */
    setEmbeddingsOverviewTableVisiblity(show)
    {
        // Create new split pane structure including embeddings overview table.
        if (show) {
            this._bottomSplitPane.setSizes([20, 40, 40]);
        }
        // Remove embeddings overview table.
        else {
            // this._bottomSplitPane.setSizes([2, 49, 49]);
            this._bottomSplitPane.collapse(0);
        }
    }

}