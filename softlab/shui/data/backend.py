"""
Basic definitions for data backend
"""
from typing import (
    Any,
    Dict,
    Optional,
    Sequence,
)
from abc import abstractmethod
from softlab.shui.data.base import (
    DataGroup,
    DataRecord,
    DataChart,
)
from softlab.shui.backend import (
    DatabaseBackend,
    catch_error,
)
import numpy as np
import pandas as pd
import h5py
import uuid
import json
import sqlite3
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__) # prepare logger

class DataBackend(DatabaseBackend):
    """
    Abstract definition of data backend, derived from ``DatabaseBackend``

    Additional actions for user:
    - list_groups -- list ID sequence of all groups in backend
    - load_group -- load a group with given ID
    - save_group -- save a group to the backend

    Methods need be implemented by derived class:
    - connect_impl -- perform actual connection
    - disconnect_impl -- perform actual disconnection
    - list_impl -- list ID sequence of all groups actually
    - load_impl -- load a group with given ID actually
    - save_impl -- save a group to the backend actually
    """

    def __init__(self, type: str) -> None:
        super().__init__(type)

    def list_groups(self) -> Sequence[str]:
        """List all IDs of groups in the backend"""
        if self.connected:
            return self.list_impl()
        else:
            raise ConnectionError('The backend has not connected')

    def load_group(self, id: str) -> Optional[DataGroup]:
        """Load a group with the given ID"""
        if self.connected:
            return self.load_impl(id)
        else:
            raise ConnectionError('The backend has not connected')

    def save_group(self, group: DataGroup) -> bool:
        """Save a group into the backend"""
        if self.connected:
            return self.save_impl(group)
        else:
            raise ConnectionError('The backend has not connected')

    @abstractmethod
    def list_impl(self) -> Sequence[str]:
        """Actual listing of group IDs, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def load_impl(self, id: str) -> Optional[DataGroup]:
        """Actual loading of a group, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def save_impl(self, group: DataGroup) -> bool:
        """Actual saving of a group, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

class HDF5DataBackend(DataBackend):
    """Data backend using HDF5. A subclass of DataBackend"""

    def __init__(self):
        super().__init__(type='hdf5')
        self.file = None

    @catch_error(failed_return=False, action='connect')
    def connect_impl(self, args: Dict[str, Any]) -> bool:
        """
        Arguments:
        - args -- hdf5 backend arguments
            - path -- absolute path to the hdf5 data file.
        """
        path = args['path'] if 'path' in args else 'data.hdf5'
        self.file = h5py.File(path, 'a')
        print(f'Connected to HDF5 backend, data is stored in {path}.')
        return True

    @catch_error(failed_return=False, action='disconnect')
    def disconnect_impl(self) -> bool:
        self.file.close()
        self.file = None
        return True

    @catch_error(failed_return=[], action='list groups')
    def list_impl(self) -> Sequence[str]:
        return list(self.file.keys())

    @catch_error(failed_return=None, action='load group')
    def load_impl(self, id: str) -> Optional[DataGroup]:
        hdf5_data_grp = self.file[id]
        data_group = self.load_data_group_from_hdf5_group(hdf5_data_grp)
        data_group.backend = {
            'type': 'hdf5',
            'arguments': {'path': self.file.filename},
        }
        self.mark_success()
        return data_group

    @catch_error(failed_return=False, action='save group')
    def save_impl(self, data_grp: DataGroup) -> bool:
        """
        Save DataGroup object in hdf5 backend.

        The hierarchy of the data saved in hdf5 is:
        - ``/data_group/data_record/table/column`` or
        - ``/data_group/data_record/charts/chart``
        """
        if str(data_grp.id) in self.file:
            del self.file[str(data_grp.id)]

        hdf5_data_grp = self.file.create_group(str(data_grp.id))

        hdf5_data_grp.attrs['id'] = str(data_grp.id)
        hdf5_data_grp.attrs['name'] = str(data_grp.name)
        hdf5_data_grp.attrs['timestamp'] = data_grp.timestamp.isoformat()
        for key, value in data_grp.meta.items():
            hdf5_data_grp.attrs[key] = str(value)

        hdf5_data_grp.attrs['backend'] = json.dumps({
            'type': 'hdf5', 'arguments': {'path': self.file.filename},
        })

        # save data records
        data_record_names = data_grp.records
        for name in data_record_names:
            data_record = data_grp.record(name)
            self.save_record(hdf5_data_grp, data_record)
        self.mark_success()
        return True

    @staticmethod
    def save_record(hdf5_data_grp: h5py.Group, data_record: DataRecord) -> None:
        """
        Save a DataRecord object as a hdf5 group.

        Each column of the object's table is saved as a hdf5 dataset.
        """
        if data_record.name in hdf5_data_grp:
            del hdf5_data_grp[data_record.name]

        record_grp_to_save = hdf5_data_grp.create_group(data_record.name)
        record_grp_to_save.attrs['name'] = data_record.name

        record_columns_to_save = record_grp_to_save.create_group('columns')
        for col_info in data_record.columns:
            col_df = data_record.column(col_info['name'])
            dst = record_columns_to_save.create_dataset(
                col_info['name'],
                data=col_df.values
                )
            for attr in ['name', 'label', 'unit', 'dependent']:
                dst.attrs[attr] = col_info[attr]

        record_charts_to_save = record_grp_to_save.create_group('charts')
        for chart_title in data_record.charts:
            chart = data_record.chart(chart_title)
            dst = record_charts_to_save.create_dataset(
                chart.title,
                data=chart.figure,
            )

    @staticmethod
    def load_data_group_from_hdf5_group(hdf5_data_grp: h5py.Group):
        """
        Load DataGroup object in hdf5 backend.

        The hierarchy of the data saved in hdf5 is:
        - ``/data_group/data_record/table/column`` or
        - ``/data_group/data_record/charts/chart``
        """
        # load metadata
        meta = hdf5_data_grp.attrs
        group_name = meta.pop('name', 'group')
        group_id = uuid.UUID(meta.pop('id', uuid.uuid4()))
        timestamp = meta.pop('timestamp', datetime.now())
        backend = meta.pop('backend', '{}')
        target_data_group = DataGroup(group_name, group_id, meta)
        target_data_group.timestamp = timestamp
        target_data_group.backend = json.loads(backend)

        # load data record
        for name in hdf5_data_grp.keys():
            hdf5_data_record = hdf5_data_grp[name]

            # load data record table
            hdf5_data_record_columns = hdf5_data_record['columns']
            col_names = list(hdf5_data_record_columns.keys())
            col_metadata = [
                {
                    attr: hdf5_data_record_columns[col_n].attrs[attr]
                    for attr in ['name', 'label', 'unit', 'dependent']
                } for col_n in col_names
            ]
            data_record = DataRecord(name=name, columns=col_metadata)
            table = pd.DataFrame({
                col_name: hdf5_data_record_columns[col_name][:, 0]
                for col_name in col_names
            })
            data_record.add_rows(table)

            # load data record charts
            hdf5_data_record_charts = hdf5_data_record['charts']
            for hdf5_data_chart_title in hdf5_data_record_charts.keys():
                hdf5_chart_dst = hdf5_data_record_charts[hdf5_data_chart_title]
                chart = DataChart(title=hdf5_data_chart_title)
                chart.figure = hdf5_chart_dst[...]
                data_record.add_chart(chart)

            target_data_group.add_record(data_record)

        return target_data_group

class Sqlite3DataBackend(DataBackend):
    """Data backend using sqlite3"""

    def __init__(self):
        super().__init__('sqlite3')
        self.conn = None
        self.cur = None
        self._path = 'data.db'

    @catch_error(failed_return=False, action='connect')
    def connect_impl(self, args: Dict[str, Any]) -> bool:
        """
        Arguments:
        - args --  sqlite3 backend arguments
            - path -- absolute path to the sqlite database file
        """
        path = args['path'] if 'path' in args else 'data.db'

        def adapt_array(arr):
            """
            Adapt numpy.ndarray to sqlite binary.
            """
            out = io.BytesIO()
            np.save(out, arr)
            out.seek(0)
            return sqlite3.Binary(out.read())

        def convert_array(blob):
            """
            Convert sqlite binary to numpy.ndarray
            """
            out = io.BytesIO(blob)
            out.seek(0)
            return np.load(out)

        def adapt_dataframe(df):
            """
            Adapt pandas.DaraFrame to sqlite binary.
            """
            out = io.BytesIO()
            df.to_csv(out, index=False)
            out.seek(0)
            return sqlite3.Binary(out.read())

        def convert_dataframe(blob):
            """
            Convert sqlite binary to pandas.DataFrame
            """
            out = io.BytesIO(blob)
            out.seek(0)
            return pd.read_csv(out)

        self.conn = sqlite3.connect(
            path, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level=None)
        sqlite3.register_adapter(np.ndarray, adapt_array)
        sqlite3.register_converter('array', convert_array)
        sqlite3.register_adapter(pd.DataFrame, adapt_dataframe)
        sqlite3.register_converter('dataframe', convert_dataframe)
        sqlite3.register_adapter(dict, lambda d: json.dumps(d))
        sqlite3.register_converter('dict', lambda d: json.loads(d))
        sqlite3.register_adapter(list, lambda d: json.dumps(d))
        sqlite3.register_converter('list', lambda d: json.loads(d))

        self.cur = self.conn.cursor()

        # Data-definition Language
        self.conn.execute("begin transaction;")
        self.cur.execute(
                'create table if not exists datagroup ('
                    'id text, '
                    'experiment text, '
                    'sample text, '
                    'run_id integer, '
                    'timestamp timestamp, '
                    'backend dict, '
                    'primary key (id))'
                )
        self.cur.execute(
                'create table if not exists datarecord ('
                     'group_id text, '
                     'name text, '
                     'columns list, '
                     'df dataframe, '
                     'primary key (group_id, name), '
                     'foreign key (group_id) references datagroup(id))'
                )
        self.cur.execute(
                'create table if not exists datachart ('
                     'group_id text, '
                     'record_name text, '
                     'title text, '
                     'figure array, '
                     'primary key (group_id, record_name, title), '
                     'foreign key (group_id, record_name) '
                     'references datarecord(group_id, name))'
                )
        self.conn.execute("commit;")

        print(f'Connected to sqlite3 backend, data is stored in {path}.')
        self._path = path
        return True

    @catch_error(failed_return=False, action='disconnect')
    def disconnect_impl(self) -> bool:
        self.cur.close()
        self.conn.close()
        return True

    @catch_error(failed_return=[], action='list groups')
    def list_impl(self) -> Sequence[str]:
        res = self.conn.execute(
                    'select id '
                    'from datagroup '
                    'order by timestamp'
                    ).fetchall()
        return res

    @catch_error(failed_return=None, action='load group')
    def load_impl(self, id: str) -> Optional[DataGroup]:
        self.cur.execute(
            'select * '
            'from datagroup '
            'where id=:id',
            {'id': id}
            )
        metadata = self.cur.fetchone()
        if metadata is None:
            print(f'Group {id} does not exist.')
            return

        target_data_group = DataGroup(
            metadata[1], uuid.UUID(metadata[0]),
            {'sample': metadata[2], 'run_id': metadata[3]},
        )
        target_data_group.timestamp = metadata[4]
        target_data_group.backend = {
            'type': self.backend_type,
            'arguments': {'path': self._path}
        }

        # recover data records in the data group
        self.cur.execute(
            'select name, columns, df '
            'from datarecord '
            'where group_id=:id',
            {'id': id},
        )
        records_data = self.cur.fetchall()
        for record_name, columns, df in records_data:
            data_record = DataRecord(name=record_name, columns=columns)
            data_record.add_rows(df)
            charts_data = self.cur.execute(
                'select title, figure '
                'from datachart '
                'where group_id=:group_id and '
                'record_name=:record_name',
                {'group_id': id, 'record_name': record_name}
            ).fetchall()
            for title, figure in charts_data:
                chart = DataChart(title=title)
                chart.figure = figure
                data_record.add_chart(chart)
            target_data_group.add_record(data_record)
        self.mark_success()
        return target_data_group

    @catch_error(failed_return=False, action='save group')
    def save_impl(self, group: DataGroup) -> bool:
        """
        Save DataGroup object in hdf5 backend.
        """
        self.conn.execute("begin transaction;")
        self.cur.execute(
            'delete from datagroup '
            'where id=:id',
            {'id': str(group.id)}
        )
        self.cur.execute(
            'insert into datagroup values(?, ?, ?, ?, ?, ?)',
            (str(group.id), group.name, group.meta.get('sample', 'demo'),
             group.meta.get('run_id', 0), group.timestamp, group.backend)
        )

        self.cur.execute(
            'delete from datarecord '
            'where group_id=:id',
            {'id': str(group.id)}
        )

        record_names = group.records
        for record_name in record_names:
            record = group.record(record_name)
            self.cur.execute(
                'insert into datarecord values(?, ?, ?, ?)',
                (str(group.id), record_name, record.columns, record.table)
            )

            self.cur.execute(
                'delete from datachart '
                'where group_id=:id and record_name=:name',
                {'id': str(group.id), 'name': record_name}
            )
            for chart_title in record.charts:
                chart = record.chart(chart_title)
                self.cur.execute(
                    'insert into datachart values(?, ?, ?, ?)',
                    (str(group.id), record_name, chart_title, chart.figure)
                )

        self.conn.execute("commit;")
        self.mark_success()
        return True

def get_data_backend(type: str, 
                     args: Optional[Dict[str, Any]] = None,
                     connect: bool = True) -> DataBackend:
    """
    Get data backend

    Arguments:
    - type -- backend type
    - args -- connect arguments
    - connect -- whether to connect at beginning

    Returns:
    the backend with the given type

    Throws:
    - If the given type is empty, raise a value error
    - If there is no backend implementation of the given type, raise a
      not-implemented error
    """
    backend_type = str(type)
    if len(backend_type) == 0:
        raise ValueError('Backend type is empty')
    if backend_type == 'hdf5':
        backend = HDF5DataBackend()
    elif backend_type == 'sqlite3':
        backend = Sqlite3DataBackend()
    else:
        raise NotImplementedError(
            f'Backend of type {type} is not implemented'
        )
    if connect:
        if not backend.connect(args):
            _logger.warning(f'Failed to connect: {backend.last_error}')
    return backend

def get_data_backend_by_info(info: Dict[str, Any], 
                             connect: bool = True) -> DataBackend:
    """
    Get data backend by using the given information

    Arguments:
    - info -- backend information, 'type' key is necessary, and the optional
            key 'arguments' related to connect arguments
    - connect -- whether to connect at beginning

    Returns:
    the backend with the given type

    Throws:
    - If the given info is not a dictionary, raise a type error
    """
    if not isinstance(info, Dict):
        raise TypeError(f'Type of info is invalid: {type(info)}')
    return get_data_backend(info['type'], info.get('arguments', None), connect)

if __name__ == '__main__':
    backend = HDF5DataBackend()
    print('type: ', backend.backend_type)
    print('status: ', backend.status)
    print('connected: ', backend.connected)
    backend.connect()
    print('status: ', backend.status)
    print('connected: ', backend.connected)
    dg1 = DataGroup('example')
    print('data group id: ', dg1.id)

    columns = [
        {'name': 'x',
         'label': 'x',
         'dependent': False},
        {'name': 'y',
         'label': 'y',
         'dependent': True}
    ]
    data = np.array([[1, 1],
                     [2, 4],
                     [3, 9],
                     [4, 16]])
    dr1 = DataRecord('dr1', columns, data)
    dc = DataChart('test')
    dc.figure = np.random.randint(155, size=(10, 10))
    dr1.add_chart(dc)
    dg1.add_record(dr1)
    backend.save_group(dg1)
    print(backend.list_groups())

    dg1_ = backend.load_group(str(dg1.id))
    if dg1_ is None:
        print(backend.errors)
    print(f'Backend info: {dg1_.backend}')
    dr1_ = dg1_.record('dr1')
    print(dr1_.snapshot())
    print(dg1_.record('dr1').charts)
    print(dg1_.record('dr1').chart('test').figure)

    backend = get_data_backend('hdf5')
    assert(isinstance(backend, HDF5DataBackend))
    print(f'Get backend with type: {backend.backend_type}')
    print(f'Status of backend: {backend.status}')
    backend = get_data_backend_by_info({
        'type': 'sqlite3',
        'arguments': {'path': 'sqlite3.db'},
    }, connect=False)
    assert(isinstance(backend, Sqlite3DataBackend))
    assert(backend.status == DataBackend.Status.NotConnected)
    print(f'Get backend with type: {backend.backend_type}')
    print(f'Status of backend: {backend.status}')
    try:
        backend = get_data_backend('asdg')
    except NotImplementedError:
        print('No implementation for type "asdg"')
