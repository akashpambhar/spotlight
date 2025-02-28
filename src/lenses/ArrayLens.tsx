import 'twin.macro';
import { Lens } from '../types';
import JsonView from '@uiw/react-json-view';

const THEME = { backgroundColor: 'transparent' };

const ArrayLens: Lens = ({ value }) => {
    const array = value as Array<number>;

    return (
        <div tw="w-full h-full overflow-y-auto">
            <JsonView
                value={array}
                style={THEME}
                displayObjectSize={false}
                displayDataTypes={false}
                highlightUpdates={false}
                enableClipboard={false}
            />
        </div>
    );
};

ArrayLens.key = 'ArrayLens';
ArrayLens.dataTypes = ['array', 'Embedding', 'Window', 'BoundingBox'];
ArrayLens.defaultHeight = 22;
ArrayLens.minHeight = 22;
ArrayLens.maxHeight = 512;
ArrayLens.displayName = 'Array';

export default ArrayLens;
