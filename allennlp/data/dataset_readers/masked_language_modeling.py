from typing import Dict, List
import logging

from overrides import overrides

from allennlp.common.file_utils import cached_path
from allennlp.common.tqdm import Tqdm
from allennlp.data.instance import Instance
from allennlp.data.tokenizers.tokenizer import Tokenizer
from allennlp.data.tokenizers import Token, WordTokenizer
from allennlp.data.tokenizers.word_splitter import JustSpacesWordSplitter
from allennlp.data.dataset_readers.dataset_reader import DatasetReader
from allennlp.data.token_indexers.token_indexer import TokenIndexer
from allennlp.data.fields import IndexField, LabelField, ListField, TextField
from allennlp.data.token_indexers import SingleIdTokenIndexer


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@DatasetReader.register("masked_language_modeling")
class MaskedLanguageModelingReader(DatasetReader):
    """
    Reads a text file and converts it into a ``Dataset`` suitable for training a masked language
    model.

    The :class:`Field` s that we create are the following: an input ``TextField``, a mask position
    ``ListField[IndexField]``, and a target token ``ListField[LabelField]`` (which shares a vocab
    namespace with the token vocabulary).  The mask position and target token lists are the same
    length.

    Parameters
    ----------
    tokenizer : ``Tokenizer``, optional (default=``WordTokenizer()``)
        We use this ``Tokenizer`` for the text.  See :class:`Tokenizer`.
    token_indexers : ``Dict[str, TokenIndexer]``, optional (default=``{"tokens": SingleIdTokenIndexer()}``)
        We use this to define the input representation for the text, and to get ids for the mask
        targets.  See :class:`TokenIndexer`.
    """
    def __init__(self,
                 tokenizer: Tokenizer = None,
                 token_indexers: Dict[str, TokenIndexer] = None,
                 lazy: bool = False) -> None:
        super().__init__(lazy)
        self._tokenizer = tokenizer or WordTokenizer(word_splitter=JustSpacesWordSplitter())
        self._token_indexers = token_indexers or {"tokens": SingleIdTokenIndexer()}

    @overrides
    def _read(self, file_path: str):
        raise NotImplementedError

    @overrides
    def text_to_instance(self,
                         sentence: str = None,
                         tokens: List[Token] = None,
                         targets: List[str] = None) -> Instance:  # type: ignore
        # pylint: disable=arguments-differ
        """
        Parameters
        ----------
        sentence : ``str``, optional
            A sentence containing [MASK] tokens that should be filled in by the model.  This input
            is superceded and ignored if ``tokens`` is given.
        tokens : ``List[Token]``, optional
            An already-tokenized sentence containing some number of [MASK] tokens to be predicted.
        targets : ``List[str]``, optional
            Contains the target tokens to be predicted.  The length of this list should be the same
            as the number of [MASK] tokens in the input.
        """
        if not tokens:
            tokens = self._tokenizer.tokenize(sentence)
        input_field = TextField(tokens, self._token_indexers)
        mask_positions = []
        for i, token in enumerate(tokens):
            if token.text == '[MASK]':
                mask_positions.append(i)
        if not mask_positions:
            raise ValueError("No [MASK] tokens found!")
        if targets and len(targets) != len(mask_positions):
            raise ValueError(f"Found {len(mask_positions)} mask tokens and {len(targets)} targets")
        mask_position_field = ListField([IndexField(i, input_field) for i in mask_positions])
        target_field = TextField([Token(target) for target in targets], self._token_indexers)
        return Instance({'tokens': input_field,
                         'mask_positions': mask_position_field,
                         'target_ids': target_field})