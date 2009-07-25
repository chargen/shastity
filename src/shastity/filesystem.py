# -*- coding: utf-8 -*-

# Copyright (c) 2009 Peter Schuller <peter.schuller@infidyne.com>

"""
Provide a thin wrapper around file system operations. Reasons for
doing this include:

  - It makes it easier to unit test code that depends on file system access
    because we can more easily write mock-ups.
  - File system operations are potentially platform sensetive, so it is nice to
    have them in one place.
  - File system operations are a "dangerous" part of shastity in the sense that
    they side-effect on the surrounding environment. It is nice to avoid having
    such things spread all over the place.

Because file system access is inherently destructive in nature (i.e.,
has side-effects) we comfortable module file systems as class
instances.

Note that our "file system" concept is not the same as that of an
operating system; to us, a file system is basically "files and
directories accessible by the process via the native system's API". We
do not intend to imply any specific knowledge about OS file system
mount points, types, or anything like that.
"""

from __future__ import absolute_import
from __future__ import with_statement

import errno
import os
import os.path
import shutil
import tempfile

class FileMetaData(object):
    '''Represents meta-data about files, including any and all
    meta-data that are to be preserved on backup/restore.
    
    We make a deliberate effort to provide a high-level abstraction
    rather than POSIX style bit twiddling. We essentially provide a
    dedicated accessor for every relevant piece of information, along
    with methodsfor converting to/from a text format readable both by
    humans (sort of) and ourselves.

    Instances of this class only care about meta data; they know
    nothing of the files to which the meta data appliies, or
    underlying file system operations (construction of FileMetaData
    instances from some actual real file is done by the appropriate
    file system backend).

    Instances of this class are to be treated as read-only, and the
    public interface deliberately makes it difficult to make changes.

    @ivar is_directory        Is the file a directory?
    @ivar is_character_device Is the file a special character device?
    @ivar is_block_device     Is the file a block device?
    @ivar is_regular          Is the file a regularfile?
    @ivar is_fifo             Is the file a FIFO/named pipe?
    @ivar is_symlink          Is the file a symbolic link?
    @ivar uid                 UID of the owner.
    @ivar gid                 GID of the group owner.
    @ivar size                Size of file (if regular, else None).
    @ivar atime               Access time of the file (seconds since epoch).
    @ivar mtime               Modification time of the file (seconds since epoch).
    @ivar ctime               ctime, whatever the platform feels that means (secondssince epoch).
    @ivar is_setuid           Is the setuid bit set?
    @ivar is_setgid           Is the setgid bit set?
    @ivar is_sticky           Is the sticky bit set?
    @ivar yser_read
    @ivar group_read
    @ivar other_read
    @ivar user_write
    @ivar group_write
    @ivar other_write
    @ivar user_execute
    @ivar group_execute
    @ivar other_execute
    '''
    def __init__(self, props=None, other=None):
        '''
        @param props: Dict of properties that match those of the instance to be created.
        @param other: Other instance on which to base the values of any properties that
                      do not appear in props.
        '''
        pass

    @classmethod
    def from_string(cls, s):
        '''Given a string in the format produced by to_string(), parse
        it and return the resulting instance.'''
        raise NotImplementedError

    def to_string(self):
        '''Produce a string encoding of this meta data.

        TODO: define format characteristics'''
        raise NotImplementedError

    @property
    def is_directory(self):
        return self.__is_directory

    @property
    def is_character_device(self):
        return self.__is_character_device

    @property
    def is_block_device(self):
        return self.__is_block_device

    @property
    def is_regular(self):
        return self.__is_regular

    @property
    def is_fifo(self):
        return self.__is_fifo

    @property
    def is_symlink(self):
        return self.__is_symlink

    @property
    def uid(self):
        return self.__uid

    @property
    def gid(self):
        return self.__gid

    @property
    def size(self):
        return self.__size

    @property
    def atime(self):
        return self.__atime

    @property
    def mtime(self):
        return self.__mtime

    @property
    def ctime(self):
        return self.__ctime

    @property
    def is_setuid(self):
        return self.__is_setuid

    @property
    def is_setgid(self):
        return self.__is_setgid
    
    @property
    def is_sticky(self):
        return self.__is_sticky

    @property
    def user_read(self):
        return self.__user_read

    @property
    def group_read(self):
        return self.__user_read

    @property
    def other_read(self):
        return self.__other_read

    @property
    def user_write(self):
        return self.__user_write
    
    @property
    def group_write(self):
        return self.__group_write

    @property
    def other_write(self):
        return self.__other_write

    @property
    def user_execute(self):
        return self.__user_execute

    @property
    def group_execute(self):
        return self.__group_execute
    
    @property
    def other_execute(self):
        return self.__other_execute

class StaleTemporaryDirectory(Exception):
    '''Raised to indicate that an attempt to use a stale (cleaned up)
    temporary directory was detected.'''
    pass

class TemporaryDirectory(object):
    '''An automatically cleaning temporary directory. The preferred
    use is with the 'with' statement, but calling code may also
    close() it explicitly. It will also close on GC.

    Most users will only be interested in the 'path' attribute of a
    temporary directory object.

    @ivar fs The file system with which the temporary directory is associated.
    @ivar path The path to the temporary directory.'''
    def __init__(self, fs, path):
        assert isinstance(fs, FileSystem)

        self.__fs = fs
        self.__path = path
        self.__stale = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if not self.__stale:
            self.__stale = True
            self.__fs.rmtree(self.__path)

    def __get_fs(self):
        if self.__stale:
            raise StaleTemporaryDirectory(self.__path)
        return self.__fs
        
    def __get_path(self):
        if self.__stale:
            raise StaleTemporaryDirectory(self.__path)
        return self.__path

    fs = property(__get_fs)
    path = property(__get_path)

class FileSystem(object):
    ''' Abstract base class of file systems (see module documentation
    for our definition of file system). This defines the interface to
    be implemented by file systems.

    Unless otherwise noted, methods with obvious POSIX counterparts
    will have matching semantics.

    In general, failure cases are those of POSIX.
    '''
    def mkdir(self, path):
        raise NotImplementedError

    def rmdir(self, path):
        raise NotImplementedError

    def unlink(self, path):
        raise NotImplementedError

    def symlink(self, src, dst):
        raise NotImplementedError

    def exists(self, path):
        return os.path.exists(path)

    def open(self, path, mode):
        raise NotImplementedError

    def is_symlink(self, path):
        '''@return Whether the given path is a symlink.'''
        raise NotImplementedError

    def is_dir(self, path):
        '''@return Whether the given path is a directory (or symlink pointing to one).'''
        raise NotImplementedError

    def listdir(self, path):
        '''@return List of filenames in the given directory.'''
        raise NotImplementedError

    def rmtree(self, path):
        '''Recursively delete the tree rooted at path (not following
        symlinks).'''
        # we implement this ourselves, rather than using
        # shutil.rmtree(), in order to have the same implementation
        # for regular fs and memory fs.
        if self.is_dir(path):
            for fname in self.listdir(path):
                self.rmtree(os.path.join(path, fname))
            self.rmdir(path)
        else:
            self.unlink(path)

    def mkdtemp(self, suffix=None):
        '''Atomically create/allocate a temporary directory and return
        its name.
        
        @note While similar, this is not identical to python's tempfile.mkdtemp().

        @param suffix: Suffix to apply to the allocated name, if supported.

        @return The absolute path of the temporary directory. '''
        raise NotImplementedError

    def tempdir(self, suffix=None):
        '''Allocate a temporary directory and return a
        TemporaryDirectory instance backed by this file system.

        @note This method has a default implementation in the abstract
              base class which is implemented in terms of mkdtemp().'''
        dirname = self.mkdtemp()
        return TemporaryDirectory(self, dirname)

class LocalFileSystem(FileSystem):
    def mkdir(self, path):
        os.mkdir(path)

    def rmdir(self, path):
        os.rmdir(path)

    def unlink(self, path):
        os.unlink(path)

    def symlink(self, src, dst):
        os.symlink(src, dst)

    def open(self, path, mode):
        return open(path, mode)

    def is_symlink(self, path):
        return os.path.islink(path)

    def is_dir(self, path):
        return os.path.isdir(path)

    def listdir(self, path):
        '''@return List of filenames in the given directory.'''
        return os.listdir(path)

    def mkdtemp(self, suffix=None):
        # mkdtemp differentiates between None and no parameter
        return tempfile.mkdtemp(suffix=('' if suffix is None else suffix))

class MemoryDirectory:
    def __init__(self, parent):
        self.parent = parent
        self.entries = dict()

    def __getitem__(self, fname):
        if not fname in self.entries:
            raise OSError(errno.ENOENT, 'file not found')

        return self.entries[fname]

    def __contains__(self, fname):
        return fname in self.entries

    def root(self):
        if self.parent:
            return self.parent.root()
        else:
            return self

    def lookup(self, comps, no_follow=False):
        if comps:
            if comps[0] == '/':
                return self.root().lookup(comps[1:], no_follow=no_follow)
            elif comps[0] in self.entries:
                # we don't recurse for non-directories mainly because
                # symlinks don't know their parent
                entry = self.entries[comps[0]]
                if isinstance(entry, MemoryDirectory):
                    return entry.lookup(comps[1:], no_follow=no_follow)
                elif isinstance(entry, MemoryFile):
                    if len(comps) > 1:
                        raise OSError(errno.ENOTDIR, 'not a directory')
                    else:
                        return entry
                elif isinstance(entry, MemorySymlink):
                    if no_follow:
                        raise AssertionError('no_follow, but requested demanded follow')
                    else:
                        # ask symlink to resolve itself relative to us
                        return entry.resolve(self)
                else:
                    raise AssertionError('this code should not be reachable')
            else:
                raise OSError(errno.ENOENT, 'file not found')
        else:
            return self

    def is_empty(self):
        return not self.entries

    def is_dir(self):
        return True
    
    def is_symlink(self):
        return False

    def listdir(self):
        return self.entries.keys()
    
    def deparent(self):
        self.parent = None

    def mkdir(self, name):
        if name in self.entries:
            raise OSError(errno.EEXIST, 'file exists')
        self.entries[name] = MemoryDirectory(parent=self)

    def rmdir(self, name):
        if name not in self.entries:
            raise OSError(errno.ENOENT, 'file not found')
        
        if not isinstance(self.entries[name], MemoryDirectory):
            raise OSError(errno.ENOTDIR, 'not a directory')

        if not self.entries[name].is_empty():
            raise OSError(errno.ENOTEMPTY, 'directory not empty')
        
        del(self.entries[name])

    def exists(self, name):
        if not name in self.entries:
            return False

        entry = self.entries[name]
        if isinstance(entry, MemorySymlink):
            try:
                entry.resolve(self)
                return True
            except OSError, e:
                if e.errno == errno.ENOENT:
                    return False
                raise
        else:
            return True

    def link(self, memfile, name):
        if name in self.entries:
            raise OSError(errno.EEXIST, 'file exists - cannot link by that name')

        self.entries[name] = memfile

    def symlink(self, linkstring, name):
        if name in self.entries:
            raise OSError(errno.EEXIST, 'file exists')

        self.entries[name] = MemorySymlink(linkstring)
    
    def unlink(self, name):
        if not name in self.entries:
            raise OSError(errno.ENOENT, 'file not found')

        entry = self.entries[name]

        if isinstance(entry, MemoryDirectory):
            raise OSError(errno.EISDIR, 'cannot unlink directory - use rmdir()')
        elif isinstance(entry, MemorySymlink):
            del(self.entries[name])
        elif isinstance(entry, MemoryFile):
            del(self.entries[name])
        else:
            raise AssertionError('unknown entry type %s' % (entry.__class__,))

class MemorySymlink:
    def __init__(self, dest):
        '''@param dest: list (starts with . or /) of components'''
        self.dest = dest

    def is_dir(self):
        return False

    def is_symlink(self):
        return True
    
    def resolve(self, reldir):
        '''Resolve this symlink relative to the given directory.'''
        if self.dest[0] == '/':
            next_node = reldir.root()
        elif self.dest[0] == '.':
            next_node = reldir
        elif self.dest[0] == '..':
            next_node = reldir.parent
            if not next_node:
                raise OSError(errno.ENOENT, 'file not found (symlink past root node)')
        else:
            raise AssertionError('bug - bad start of symlink')

        return next_node.lookup(self.dest[1:])

    def readlink(self):
        return reduce(os.path.join, self.dest, '')

class MemoryFile:
    def __init__(self):
        self.contents = ''

    def is_dir(self):
        return False

    def is_symlink(self):
        return False

class OpenMode:
    '''Trivial helper to interpret fopen() style modestrings.

    @ivar reading_allowed
    @ivar writing_allowed
    @ivar truncate_on_open
    @ivar create_on_open
    @ivar at_beginning
    @ivar at_end
    @ivar append_only'''
    def __init__(self, modestring):
        if modestring == 'r':
            self.reading_allowed = True
            self.writing_allowed = False
            self.truncate_on_open = False
            self.create_on_open = False
            self.at_beginning = True
            self.at_end = not self.at_beginning
            self.append_only = False
        elif modestring == 'r+':
            self.reading_allowed = True
            self.writing_allowed = True
            self.truncate_on_open = False
            self.create_on_open = False
            self.at_beginning = True
            self.at_end = not self.at_beginning
            self.append_only = False
        elif modestring == 'w':
            self.reading_allowed = False
            self.writing_allowed = True
            self.truncate_on_open = True
            self.create_on_open = True
            self.at_beginning = True
            self.at_end = not self.at_beginning
            self.append_only = False
        elif modestring == 'w+':
            self.reading_allowed = True
            self.writing_allowed = True
            self.truncate_on_open = True
            self.create_on_open = True
            self.at_beginning = True
            self.at_end = not self.at_beginning
            self.append_only = False
        elif modestring == 'a':
            self.reading_allowed = False
            self.writing_allowed = True
            self.truncate_on_open = False
            self.create_on_open = True
            self.at_beginning = False
            self.at_end = not self.at_beginning
            self.append_only = True
        elif modestring == 'a+':
            self.reading_allowed = True
            self.writing_allowed = True
            self.truncate_on_open = False
            self.create_on_open = True
            self.at_beginning = False
            self.at_end = not self.at_beginning
            self.append_only = True
        else:
            raise AssertionError('invalid mode string: %s' % (modestring,))

class MemoryFileObject:
    '''File-like object for the memory file system.

    @note We do not implement sparse file semantics.
    @note Several methods remain unimplemented.
    @note We are not efficient in general, just functional.'''
    def __init__(self, memfile, mode):
        '''@type mode OpenMode'''
        self.memfile = memfile
        self.mode = mode

        if self.mode.truncate_on_open:
            self.memfile.contents = ''
        self.pos = 0 if self.mode.at_beginning else len(memfile.contents)
        
    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        pass # nothing to be done

    def flush(self):
        pass

    def fileno(self):
        raise NotImplementedError('fileno() not supported for memory fs')

    def isatty(self):
        return False

    def next(self):
        raise NotImplementedError('next() not yet implemented for memory fs')

    def read(self, size=-1):
        if size == 0:
            return ''
        elif size < 0:
            ret = self.memfile.contents[self.pos:]
            self.pos += len(ret)
            return ret
        else:
            ret = self.memfile.contents[self.pos:self.pos + size]
            self.pos += len(ret)
            return ret

    def readline(self, size=-1):
        # \r?
        if size <= 0:
            size = len(self.memfile.contents) - self.pos
        nlpos = self.memfile.contents.find('\n', self.pos, self.pos + size)

        if nlpos == -1:
            ret = self.memfile.contents[self.pos, self.pos + size]
            self.pos += len(ret)
            return ret
        else:
            ret = self.memfile.contents[self.pos, nlpos + 1]
            self.pos += len(ret)
            return ret

    def readlines(self, sizehint=None):
        raise NotImplementedError

    def xreadlines(self):
        raise NotImplementedError

    def seek(self, offset, whence=os.SEEK_SET):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def truncate(self, size=0):
        self.memfile.contents = self.memfile.contents[0:size + 1]
        
    def write(self, str):
        self.memfile.contents = self.memfile.contents[0:self.pos + 1] + str + self.memfile.contents[self.pos + 1:]

    def writelines(self, sequence):
        raise NotImplementedError
            
class MemoryFileSystem(FileSystem):
    '''A simple in-memory file system primarily intended for unit testing.

    Implementation notes
    ====================

    TODO: talk about permissions
    TODO: talk about concurrency'''

    def __init__(self):
        # Internally we use MemoryDirectory, MemorySymlink, MemoryFile
        # and MemoryFileObject to accomplish our goal.
        # 
        # We are mostly responsible for converting between string
        # based paths (a/b/c) to component based paths (['a', 'b',
        # 'c']) and implementing logic which is beyond the scope of
        # individual instances of the classes mentioned.

        self.__root = MemoryDirectory(parent=None)
        self.__root.link(MemoryDirectory(parent=self.__root), 'tmp')

        self.__tmp_count = 0   # Used to allocate unique temp names
        self.__cwd = self.__root

    def __split_slash_agnostically(self, path):
        directory, file = os.path.split(path)
        if not file:
            directory, file = os.path.split(directory)

        assert directory, 'directory expected on input path %s' % (path,)
        assert file, 'file expected on input path %s' % (file,)

        return (directory, file)

    def __tokenize(self, path):
        if len(path) > 1 and path.endswith('/'):
            path = path[0:len(path) - 1]

        while path.find('//') != -1:
            path.replace('//', '/')

        if path.startswith('/'):
            if len(path) > 1:
                return ['/'] + path[1:].split('/')
            else:
                return ['/']
        else:
            return path.split('/')

    def __lookup(self, path):
        # todo: abs vs. rel
        return self.__root.lookup(self.__tokenize(path))

    def mkdir(self, path):
        dname, fname = self.__split_slash_agnostically(path)
        d = self.__lookup(dname)

        if not d.is_dir():
            raise OSError(errno.ENOTDIR, 'not a directory (%s)' % (directory,))

        d.mkdir(fname)

    def rmdir(self, path):
        if path == '/':
            raise OSError(errno.EINVAL, 'invalid argument - cannot rmdir /')

        dname, fname = self.__split_slash_agnostically(path)
        d = self.__lookup(dname)

        d.rmdir(fname)

    def unlink(self, path):
        if path == '/':
            raise OSError(errno.EINVAL, 'invalid argument - cannot unlink /')

        dname, fname = self.__split_slash_agnostically(path)
        d = self.__lookup(dname)

        d.unlink(fname)

    def symlink(self, src, dst):
        dname, fname = self.__split_slash_agnostically(dst)
        d = self.__lookup(dname)

        d.symlink(self.__tokenize(src), fname)

    def exists(self, path):
        try:
            self.__lookup(path)
            return True
        except OSError, e:
            if e.errno == errno.ENOENT:
                return False
            else:
                raise

    def open(self, path, modestring):
        mode = OpenMode(modestring)
        if mode.create_on_open:
            if not self.exists(path):
                dname, fname = self.__split_slash_agnostically(path)
                self.__lookup(dname).link(MemoryFile(), fname)
        return MemoryFileObject(self.__lookup(path), mode)

    def is_symlink(self, path):
        dname, fname = self.__split_slash_agnostically(path)
        d = self.__lookup(dname)

        if not d.is_dir():
            raise OSError(errno.EISDIR, 'is a directory')

        return d[fname].is_symlink()

    def is_dir(self, path):
        return self.__lookup(path).is_dir()

    def listdir(self, path):
        if not self.is_dir(path):
            raise OSError(errno.ENOTDIR, 'not a directory')

        return self.__lookup(path).listdir()

    def mkdtemp(self, suffix=None):
        tmpname = 'tmp%s' % (str(self.__tmp_count),)
        self.__tmp_count += 1

        # we may legitimately collide since we blindly hope no one
        # created a matching file, or /tmp could be removed
        d = self.__lookup('/tmp')
        fullname = '%s%s' % (tmpname, ('-%s' % (suffix,)) if suffix else '')

        d.link(MemoryDirectory(parent=d), fullname)

        return '/tmp/%s' % (fullname,)

    def tempdir(self, suffix=None):
        return TemporaryDirectory(self, self.mkdtemp())
    
        
