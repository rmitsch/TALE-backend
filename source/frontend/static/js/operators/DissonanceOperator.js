import Operator from "./Operator.js";
import DissonancePanel from "../panels/DissonancePanel.js";


/**
 * Class for dissonance operators (i. e. for showing disagreement between generated
 * models on particular instances/local scale).
 * One operator operates on exactly one dataset (-> one instance of class DRMetaDataset).
 */
export default class DissonanceOperator extends Operator
{
    /*
     * Constructs new DissonanceOperator.
     * @param name
     * @param stage
     * @param dataset Instance of DRMetaDataset class.
     * @param parentDivID
     */
    constructor(name, stage, dataset, parentDivID)
    {
        super(name, stage, "1", "0", dataset, parentDivID);

        // Update involved CSS classes.
        $("#" + this._target).addClass("dissonance-operator");

        // Construct all necessary panels.
        this.constructPanels();
    }

    /**
     * Constructs all panels required by this operator.
     */
    constructPanels()
    {
        // Construct panel for surrogate model visualization.
        let dissPanel = new DissonancePanel(
            "Model Disagreement",
            this
        );
        this._panels[dissPanel.name] = dissPanel;
    }

    render()
    {
        for (let panelName in this._panels) {
            this._panels[panelName].render();
        }
    }
}