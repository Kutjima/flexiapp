import uuid
import math
import pathlib
import sqlalchemy as sqlal

from typing import Any, Callable, Optional, Union
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column


FLEXIAPP_PATH = pathlib.Path(__file__).resolve().parent


def deep_access(this: object, dotted_name: str, default_value: Any = None, callback: Optional[Callable[[Any], Any]] = None) -> Any:
    value = default_value

    for name in dotted_name.split('.'):
        if (value := getattr(this, name, None)):
            if isinstance(value, object):
                this = value
        else:
            return default_value
    
    if callable(callback):
        return callback(value)

    return value


class Fleximodel(DeclarativeBase):
    __SQLALCHEMY_ENGINE__: sqlal.Engine = False

    id: Mapped[int] = mapped_column(sqlal.Integer, primary_key=True)

    @classmethod
    def bind_engine(cls, engine: sqlal.Engine):
        cls.__SQLALCHEMY_ENGINE__ = engine  

    def session(callback: Callable[[Session, Any], Any]):
        if Fleximodel.__SQLALCHEMY_ENGINE__:
            return
        
        def wrapper(*args, **kwargs):
            with Session(Fleximodel.__SQLALCHEMY_ENGINE__) as session:
                return callback(session, *args, **kwargs)
            
        return wrapper


    def bind(callback: Callable[[Session, Any], Any], *args, **kwargs):
        if not Fleximodel.__SQLALCHEMY_ENGINE__:
            return
        
        with Session(Fleximodel.__SQLALCHEMY_ENGINE__) as session:
            return callback(session, *args, **kwargs)

    @classmethod
    def pk_name(cls) -> tuple[str]:
        return (column.name for column in sqlal.inspect(cls).primary_key)
    
    @classmethod
    def relationships(cls) -> list[str]:
        return [column for column, _ in sqlal.inspect(cls).relationships.items()]          

    @classmethod
    def load(cls, ident: Union[int, tuple, dict], bind_into: Optional[Callable[['Fleximodel',], 'Fleximodel']] = None) -> Optional['Fleximodel']:
        return Fleximodel.Select(cls).load(cls, ident, bind_into)

    @classmethod
    def select(cls, offset: int = 1, max_items: int = 15) -> 'Fleximodel.Select':
        try:
            offset = int(offset)

            if offset > 0:
                offset = offset - 1
            else:
                offset = 0
        except:
            offset = 0

        return Fleximodel.Select(cls, sqlal.func.count('*').over().label('__total_items_count__')).limit(max_items).offset(offset * max_items)


    def get(self, dotted_name: str, default_value: Any = None, callback: Optional[Callable[[Any], Any]] = None) -> Optional[Any]:
        return deep_access(self, dotted_name, default_value, callback)

    class Select(sqlal.Select):
        inherit_cache = True

        def load(self, model: 'Fleximodel', ident: Union[int, tuple, dict], bind_into: Optional[Callable[[Any,], Any]] = None) -> Optional['Fleximodel']:
            if not callable(bind_into):
                bind_into = lambda x: x
                    
            with Session(Fleximodel.__SQLALCHEMY_ENGINE__) as session:
                if isinstance(ident, tuple):
                    ident = {pk_name: ident[i] for i, pk_name in enumerate(self.pk_name())}

                if (item := session.query(model).get(ident)):
                    return bind_into(item)
                
        def fetch(self, params: dict = {}, bind_into: Optional[Callable[[Any,], Any]] = None):
            if not callable(bind_into):
                bind_into = lambda x: x

            with Session(Fleximodel.__SQLALCHEMY_ENGINE__) as session:
                if (item := session.execute(self, params).fetchone()):
                    if isinstance(item[0], Fleximodel):
                        return bind_into(item[0])
                    
                    return bind_into(item._mapping)

        def fetch_all(self, params: dict = {}, bind_into: Optional[Callable[[Any,], Any]] = None) -> tuple[list[Any], int, int, int]:
            if not callable(bind_into):
                bind_into = lambda x: x

            with Session(Fleximodel.__SQLALCHEMY_ENGINE__) as session:
                if not [column for column in self._all_selected_columns if column._label == '__total_items_count__']:
                    self.add_columns(sqlal.func.count('*').over().label('__total_items_count__'))

                if (items := session.execute(self, params).fetchall()):
                    if isinstance(items[0][0], Fleximodel):
                        return ([bind_into(item[0]) for item in items], items[0][1], self._offset, self._limit)
                    
                    return ([bind_into(item._mapping) for item in items], items[0]._mapping['__total_items_count__'], self._offset, self._limit)
            
            # results, total_count, offset, offset_limit
            return ([], 0, 0, 0)


class T(object):

    def __init__(self, properties: dict = {}):
        self.build(properties)
        self.__properties__ = properties
        self.__total_items_count__: int = -1

    def build(self, properties: dict) -> 'T':
        for name, value in properties.items():
            if isinstance(value, dict):
                setattr(self, name, T(value))
            else:
                setattr(self, name, value)
        
        return self
    
    def count(self) -> int:
        return self.__total_items_count__
    
    def props(self) -> int:
        return self.__properties__
    
    def get(self, dotted_name: str, default_value: Any = None, callback: Optional[Callable[[Any], Any]] = None) -> Any:
        return deep_access(self, dotted_name, default_value, callback)
    
    def set(self, dotted_name: str, value: Any, raise_exception: bool = True) -> bool:
        this = self
        last_name = None

        for name in dotted_name.split('.'):
            if (old_value := getattr(this, name, None)):
                last_name = name

                if isinstance(old_value, object) and type(old_value).__name__ not in dir(__builtins__):
                    this = old_value

        if last_name is not None:
            try:
                return setattr(this, last_name, value) or True
            except Exception as e:
                if raise_exception:
                    raise e
                
                return False
            
    @Fleximodel.session
    def load(session: Session, self, statement: Union[str, sqlal.Select], params: dict = {}, execution_options: dict = {}) -> Optional['T']:
        if (r := session.execute(sqlal.text(statement) if isinstance(statement, str) else statement, params, execution_options=execution_options).fetchone()):
            return self.build(r._mapping)
    
    @Fleximodel.session
    def fetch(session: Session, self, statement: Union[str, sqlal.Select], params: dict = {}, execution_options: dict = {}) -> Optional['T']:
        if (r := session.execute(sqlal.text(statement) if isinstance(statement, str) else statement, params, execution_options=execution_options).fetchone()):
            return T(self.__properties__).build(r._mapping)
    
    @Fleximodel.session
    def fetch_all(session: Session, self, statement: Union[str, sqlal.Select], params: dict = {}, execution_options: dict = {}) -> list['T']:
        return [T(self.__properties__).build(r._mapping) 
                for r in session.execute(sqlal.text(statement) if isinstance(statement, str) else statement, params, execution_options=execution_options).fetchall()]


class Flexihtml:

    @property
    def logo_image(self) -> str:
        return self.__logo_image
    
    @property
    def title(self) -> str:
        return self.__title
    
    @property
    def description(self) -> str:
        return self.__description
    
    @property
    def breadcrumb(self) -> 'Flexihtml.Breadcrumb':
        return self.__breadcrumb
    
    @property
    def tabs(self) -> 'Flexihtml.Tabs':
        return self.__tabs

    @property
    def table(self) -> 'Flexihtml.Table':
        return self.__table
    
    @property
    def searchbox(self) -> 'Flexihtml.Searchbox':
        return self.__searchbox

    def __init__(self, title: str = '', description: str = ''):
        self.__logo_image: str = '/flexiapp/public/images/bootstrap-logo.svg'
        self.__title: str = title
        self.__description: str = description

        self.__tabs: Flexihtml.Tabs = Flexihtml.Tabs()
        self.__breadcrumb: Flexihtml.Breadcrumb = Flexihtml.Breadcrumb()
        self.__table: Flexihtml.Table = Flexihtml.Table()
        self.__searchbox: Flexihtml.Searchbox = Flexihtml.Searchbox()
    
    def set_logo_image(self, logo_image: str):
        self.__logo_image = logo_image

    def set_title(self, title: str):
        self.__title = title

    def set_description(self, description: str):
        self.__description = description

    class Tabs:

        def __init__(self):
            self.__items: list[tuple[str, str]] = []

        def __call__(self) -> list[tuple[str, str]]:
            return self.__items

        def add(self, path: str, label: str, icon: str = '<i class="fa-solid fa-desktop"></i>'):
            self.__items.append((path, label, icon))

    class Breadcrumb:

        def __init__(self):
            self.__items: list[tuple[str, str]] = []

        def __call__(self) -> list[tuple[str, str]]:
            return self.__items

        def add(self, label: str, path: str = ''):
            self.__items.append((path, label))
    
    class Table:

        MAX_ITEMS_PER_PAGE: int = 15
        PAGINATION_PAGE_QNAME: str = 'pg'
        PAGINATION_MAX_BUTTONS: int = 11

        @property
        def offset(self) -> int:
            return self.__offset

        @property
        def offset_limit(self) -> int:
            return self.__offset_limit
        
        @property
        def total_items(self) -> int:
            return self.__total_items

        def __init__(self):
            self.__items: dict[str, dict[str, Any]] = {}
            self.__labels: dict[str, dict[str, Any]] = {}
            self.__offset: int = 0
            self.__offset_limit: int = 0
            self.__total_items: int = 0
            self.__paginations: list[tuple[int, str, bool]] = []

        def __call__(self, items: list[object], total_items: int, offset: int = 0, item_per_page: int = MAX_ITEMS_PER_PAGE, nb_buttons: int = PAGINATION_MAX_BUTTONS) -> 'Flexihtml.Table':
            self.__total_items = total_items
            self.__offset = offset + 1
            self.__offset_limit = offset + item_per_page
            self.__paginations = []
            
            if total_items == 0:
                self.__offset = 0

            if self.__offset_limit > total_items:
                self.__offset_limit = total_items

            for item in items:
                self.__items[line_uuid := str(uuid.uuid4())[0:6]] = {}

                for column_uuid, column in self.__labels.items():
                    self.__items[line_uuid][column_uuid] = {}
                    self.__items[line_uuid][column_uuid].update(column)

                    if callable(callback := column['callback']):
                        self.__items[line_uuid][column_uuid]['callback'] = callback(item)
                    elif (method := getattr(item, callback, None)) and callable(method):
                        self.__items[line_uuid][column_uuid]['callback'] = method()
                    elif (value := getattr(item, callback, None)):
                        self.__items[line_uuid][column_uuid]['callback'] = value
                    else:
                        self.__items[line_uuid][column_uuid]['callback'] = str(callback)

            if total_items <= 0:
                return self
            
            if (current := math.ceil(offset / item_per_page) + 1) > (max_button := math.ceil(total_items / item_per_page)):
                current = max_button
            
            if current < 1:
                current = 1

            if nb_buttons >= max_button:
                nb_buttons = max_button

            if current <= nb_buttons / 2:
                self.__paginations = [i + 1 for i in range(0, nb_buttons)]
            elif current > max_button - (nb_buttons / 2):
                self.__paginations = [i + 1 for i in range(max_button - nb_buttons, max_button)]
            else:
                self.__paginations = [i + 1 for i in range(current - math.ceil(nb_buttons / 2), current + math.floor(nb_buttons / 2))]

            if not self.__paginations:
                return self

            for i, n in enumerate(self.__paginations):
                self.__paginations[i] = (n, str(n), n == current)
            
            if self.__paginations[0][0] > 1:
                self.__paginations.insert(0, (1, '1 ... ', False))
            
            if self.__paginations[-1][0] < max_button:
                self.__paginations.append((max_button, f' ... {max_button}', False))

            return self

        def items(self) -> tuple[str, dict[str, Any]]:
            return self.__items.items()

        def labels(self) -> tuple[str, dict[str, Any]]:
            return self.__labels.items()
       
        def paginations(self) -> list[tuple[int, str, bool]]:
            return self.__paginations

        def add(self, name: str, callback: Union[str, Callable[[object], str]], label: str = '', hidden: int = 0, sortable: int = 1, classname: str = ''):
            self.__labels[str(uuid.uuid5(uuid.NAMESPACE_OID, name))[0:6]] = {
                'name': name,
                'callback': callback,
                'label': label if label else name.title(),
                'hidden': hidden,
                'sortable': sortable,
                'classname': classname
            }


    class Searchbox:
        
        INPUT_TYPE_TEXT: str = 'text'
        INPUT_TYPE_NUMBER: str = 'number'
        INPUT_TYPE_DATE: str = 'datetime'
        INPUT_TYPE_DATETIME: str = 'datetime'
        INPUT_TYPE_TIMESTAMP: str = 'timestamp'
        INPUT_TYPE_BOOLEAN: str = 'boolean'
        INPUT_TYPE_ENUM: str = 'enum'
        INPUT_TYPE_NULLTYPE: str = 'nulltype'
        INPUT_TYPE_LIST: str = 'list'
        INPUT_TYPE_GEOMETRY: str = 'geometry'

        KNOWN_INPUTS: dict = {
            INPUT_TYPE_TEXT: ['text', 'string', 'autostring', 'varchar', 'oid', 'inet', 'domain'],
            INPUT_TYPE_NUMBER: ['integer', 'numeric', 'smallint', 'bigint', 'real', 'double_precision'],
            INPUT_TYPE_BOOLEAN: ['bool', 'boolean'],
            INPUT_TYPE_DATE: ['datetime', 'date'],
            INPUT_TYPE_DATETIME: ['datetime', 'date'],
            INPUT_TYPE_NULLTYPE: ['nulltype'],
            INPUT_TYPE_ENUM: ['enum'],
            INPUT_TYPE_LIST: ['list', 'array'],
            INPUT_TYPE_GEOMETRY: ['geometry'],
            INPUT_TYPE_TIMESTAMP: ['timestamp'],
        }

        def __init__(self):
            self.__items: dict[str, dict[str, Any]] = {}

        def __call__(self, select: sqlal.Select, query_params: dict) -> sqlal.Select:
            for column_name, searchbox in self.items():
                sa_column = False
                sb_name = f'{column_name}_sb0'
                sb_value_1 = f'{column_name}_sb1'
                sb_value_2 = f'{column_name}_sb2'

                if searchbox['is_subquery']:
                    for sub_select in select._raw_columns:
                        if sub_select.name == column_name:
                            sa_column = sub_select
                            break
                else:
                    sa_column = searchbox['column']
                
                if sa_column is not False and (search_value_1 := query_params.get(sb_value_1, '').strip()):
                    self.__items[column_name]['input_value_1'] = search_value_1
                    self.__items[column_name]['input_value_2'] = (search_value_2 := query_params.get(sb_value_2, '').strip())
                    self.__items[column_name]['exp_selected'] = (exp := query_params.get(sb_name, '').strip())

                    if callable(callback := searchbox['callback']):
                        select = callback(select, sa_column, exp, search_value_1, search_value_2)
                    else:
                        if exp == 'is_equal':
                            select = select.where(sa_column == search_value_1)
                        elif exp == 'is_not_equal':
                            select = select.where(sa_column != search_value_1)
                        elif exp == 'is_less_than':
                            select = select.where(sa_column < search_value_1)
                        elif exp == 'is_less_equal_than':
                            select = select.where(sa_column <= search_value_1)
                        elif exp == 'is_greater_than':
                            select = select.where(sa_column > search_value_1)
                        elif exp == 'is_greater_equal_than':
                            select = select.where(sa_column >= search_value_1)
                        elif exp == 'is_like':
                            select = select.where(sa_column.ilike(f'%{search_value_1}%'))
                        elif exp == 'is_not_like':
                            select = select.where(sa_column.not_ilike(f'%{search_value_1}%'))
                        elif exp == 'is_null':
                            select = select.where(sa_column == sqlal.null())
                        elif exp == 'is_not_null':
                            select = select.where(sa_column != sqlal.null())
                        elif exp in ['is_between', 'is_not_between'] and search_value_2:
                            if exp == 'is_between':
                                select = select.where(sa_column.between(search_value_1, search_value_2))
                            else:
                                select = select.where(sqlal.not_(sa_column.between(search_value_1, search_value_2)))
                        elif exp in ['is_in', 'is_not_in']:
                            #TODO: not yet test
                            if exp == 'is_in':
                                select = select.where(sa_column.in_(search_value_1.split(',')))
                            else:
                                select = select.where(sa_column.not_in(search_value_1.split(',')))
                        elif exp in ['is_point', 'is_polygon', 'is_in_radius']:
                            continue
                        else:
                            continue

            return select
        
        def items(self) -> tuple[str, dict[str, Any]]:
            return self.__items.items()

        def add(self, column: sqlal.Column, label: str, help_text: str = '', input_value_1: Union[int, str] = '', input_value_2: Union[int, str] = '', is_subquery: bool = False):
            html_input_tag = ''
            html_input_type = ''
            exp_options = {}
            value_options = {}

            for column_type, column_types in self.KNOWN_INPUTS.items():
                if column.type.__class__.__name__.lower() in column_types:
                    if column_type in [self.INPUT_TYPE_TEXT]:
                        html_input_tag = 'textarea'
                        exp_options = {
                            '': '---',
                            'is_equal': 'is equal',
                            'is_not_equal': 'is not equal',
                            'is_like': 'is like',
                            'is_not_like': 'is not like',
                            'is_null': 'is null',
                            'is_not_null': 'is not null',
                        }
                    elif column_type in [self.INPUT_TYPE_ENUM, self.INPUT_TYPE_BOOLEAN, self.INPUT_TYPE_NULLTYPE]:
                        html_input_tag = 'select'
                        exp_options = {
                            '': '---',
                            'is_equal': 'is',
                            'is_not_equal': 'is not',
                        }

                        if column_type == self.INPUT_TYPE_BOOLEAN:
                            value_options = {
                                0: 'False', 
                                1: 'True',
                            }
                        elif column_type == self.INPUT_TYPE_NULLTYPE:
                            value_options = {'null': 'NULL'}
                        else:
                            value_options = {}
                    elif column_type in [self.INPUT_TYPE_LIST]:
                        html_input_tag = 'textarea'
                        exp_options = {
                            '': '---',
                            'is_in': 'is in',
                            'is_not_in': 'is not in',
                        }
                    elif column_type in [self.INPUT_TYPE_GEOMETRY]:
                        html_input_tag = 'input'
                        html_input_type = 'text'
                        exp_options = {
                            '': '---',
                            'is_point': 'is point',
                            'is_polygon': 'is polygon',
                            'is_in_radius': 'is in radius',
                        }
                    else:
                        html_input_tag = 'input'

                        if column_type in [self.INPUT_TYPE_TIMESTAMP, self.INPUT_TYPE_DATE, self.INPUT_TYPE_DATETIME]:
                            html_input_type = 'date'
                        else:
                            html_input_type = self.INPUT_TYPE_NUMBER

                        exp_options = {
                            '': '---',
                            'is_equal': 'is equal',
                            'is_not_equal': 'is not equal',
                            'is_less_than': 'is less than',
                            'is_less_equal_than': 'is less equal than',
                            'is_greater_than': 'is greater than',
                            'is_greater_equal_than': 'is greater equal than',
                            'is_between': 'is between .. and ..',
                            'is_not_between': 'is not between .. and ..',
                            'is_null': 'is null',
                            'is_not_null': 'is not null',
                        }
                    break
            else:
                return

            self.__items[column.name] = {
                'column': column, 
                'label': label, 
                'help_text': help_text, 
                'html_input_tag': html_input_tag,
                'html_input_type': html_input_type, 
                'input_value_1': input_value_1,
                'input_value_2': input_value_2,
                'exp_options': exp_options, 
                'exp_selected': '',
                'value_options': value_options, 
                'callback': None,
                'is_subquery': is_subquery,
            }

        def reset_column(self, column: sqlal.Column, exp_options: dict[str, str] = {}, value_type: str = '', value_options: dict[str, str] = {}, callback: Callable[[sqlal.Select, sqlal.Column, str, str, Optional[str]], sqlal.Select] = None):
            pass
