#
import cgi
import getopt
import os
import re
import string
import sys

                                         
try:
  if tuple(sys.version_info[:3]) < (2,2,0):
    raise NotImplementedError("requires python 2.2.0 or later")
except AttributeError:   # a very old python, that lacks sys.version_info       
  raise NotImplementedError("requires python 2.2.0 or later")
                                                 
try:
  True, False, bool
except NameError:
  False = 0
  True = 1
  def bool(x):
    if x:
      return True
    else:
      return False


_RUNNING_PYCHECKER = 'pychecker.python' in sys.modules


def _GetCallingModule():
  """Returns the name of the module that's calling into this module.

  We generally use this function to get the name of the module calling a
  DEFINE_foo... function.
  """

  for depth in range(1, sys.getrecursionlimit()):
    if not sys._getframe(depth).f_globals is globals():
      module_name = __GetModuleName(sys._getframe(depth).f_globals)
      if module_name is not None:
        return module_name
  raise AssertionError("No module was found")



class FlagsError(Exception):
  """The base class for all flags errors."""
  pass


class DuplicateFlag(FlagsError):
  """Raised if there is a flag naming conflict."""
  pass


class DuplicateFlagError(DuplicateFlag):

  def __init__(self, flagname, flag_values):
    self.flagname = flagname
    message = "The flag '%s' is defined twice." % self.flagname
    flags_by_module = flag_values.FlagsByModuleDict()
    for module in flags_by_module:
      for flag in flags_by_module[module]:
        if flag.name == flagname or flag.short_name == flagname:
          message = message + " First from " + module + ","
          break
    message = message + " Second from " + _GetCallingModule()
    DuplicateFlag.__init__(self, message)


class IllegalFlagValue(FlagsError):
  """The flag command line argument is illegal."""
  pass


class UnrecognizedFlag(FlagsError):
  """Raised if a flag is unrecognized."""
  pass
class UnrecognizedFlagError(UnrecognizedFlag):
  def __init__(self, flagname):
    self.flagname = flagname
    UnrecognizedFlag.__init__(
        self, "Unknown command line flag '%s'" % flagname)


_exported_flags = {}
_help_width = 80  # width of help output


def GetHelpWidth():
  """Returns: an integer, the width of help lines that is used in TextWrap."""
  return _help_width


def CutCommonSpacePrefix(text):
 
  text_lines = text.splitlines()
  # Drop trailing empty lines
  while text_lines and not text_lines[-1]:
    text_lines = text_lines[:-1]
  if text_lines:
    # We got some content, is the first line starting with a space?
    if text_lines[0] and text_lines[0][0].isspace():
      text_first_line = []
    else:
      text_first_line = [text_lines.pop(0)]
    # Calculate length of common leading whitesppace (only over content lines)
    common_prefix = os.path.commonprefix([line for line in text_lines if line])
    space_prefix_len = len(common_prefix) - len(common_prefix.lstrip())
    # If we have a common space prefix, drop it from all lines
    if space_prefix_len:
      for index in xrange(len(text_lines)):
        if text_lines[index]:
          text_lines[index] = text_lines[index][space_prefix_len:]
    return '\n'.join(text_first_line + text_lines)
  return ''


def TextWrap(text, length=None, indent='', firstline_indent=None, tabs='    '):
  
  if length is None:
    length = GetHelpWidth()
  if indent is None:
    indent = ''
  if len(indent) >= length:
    raise FlagsError('Indent must be shorter than length')
 
  if firstline_indent is None:
    firstline_indent = ''
    line = indent
  else:
    line = firstline_indent
    if len(firstline_indent) >= length:
      raise FlagsError('First iline indent must be shorter than length')


  if not tabs or tabs == ' ':
    text = text.replace('\t', ' ')
  else:
    tabs_are_whitespace = not tabs.strip()

  line_regex = re.compile('([ ]*)(\t*)([^ \t]+)', re.MULTILINE)


  result = []
  for text_line in text.splitlines():
    
    old_result_len = len(result)
    
    for spaces, current_tabs, word in line_regex.findall(text_line.rstrip()):

      if current_tabs:
       
        if (((result and line != indent) or
             (not result and line != firstline_indent)) and line[-1] == ' '):
          line = line[:-1]
      
        if tabs_are_whitespace:
          line += tabs * len(current_tabs)
        else:
          
          word = tabs * len(current_tabs) + word

      if len(line) + len(word) > length and len(indent) + len(word) <= length:
        result.append(line.rstrip())
        line = indent + word
        word = ''
  
        if len(line) + 1 >= length:
          result.append(line.rstrip())
          line = indent
        else:
          line += ' '
     
      while len(line) + len(word) >= length:
        line += word
        result.append(line[:length])
        word = line[length:]
        line = indent
   
      if word:
        line += word + ' '
  
    if (result and line != indent) or (not result and line != firstline_indent):
      result.append(line.rstrip())
    elif len(result) == old_result_len:
      result.append('')
    line = indent

  return '\n'.join(result)


def DocToHelp(doc):
 
  doc = doc.strip()


  whitespace_only_line = re.compile('^[ \t]+$', re.M)
  doc = whitespace_only_line.sub('', doc)


  doc = CutCommonSpacePrefix(doc)

 
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)

  return doc


def __GetModuleName(globals_dict):

  for name, module in sys.modules.iteritems():
    if getattr(module, '__dict__', None) is globals_dict:
      if name == '__main__':
        return sys.argv[0]
      return name
  return None


def _GetMainModule():

  for depth in range(1, sys.getrecursionlimit()):
    try:
      globals_of_main = sys._getframe(depth).f_globals
    except ValueError:
      return __GetModuleName(globals_of_main)
  raise AssertionError("No module was found")


class FlagValues:
 
  def __init__(self):
   
    self.__dict__['__flags'] = {}
    
    self.__dict__['__flags_by_module'] = {}
  
    self.__dict__['__key_flags_by_module'] = {}

  def FlagDict(self):
    return self.__dict__['__flags']

  def FlagsByModuleDict(self):
    
    return self.__dict__['__flags_by_module']

  def KeyFlagsByModuleDict(self):
    
    return self.__dict__['__key_flags_by_module']

  def _RegisterFlagByModule(self, module_name, flag):
   
    flags_by_module = self.FlagsByModuleDict()
    flags_by_module.setdefault(module_name, []).append(flag)

  def _RegisterKeyFlagForModule(self, module_name, flag):
   
    key_flags_by_module = self.KeyFlagsByModuleDict()
   
    key_flags = key_flags_by_module.setdefault(module_name, [])
   
    if flag not in key_flags:
      key_flags.append(flag)

  def _GetFlagsDefinedByModule(self, module):
    
    if not isinstance(module, str):
      module = module.__name__

    return list(self.FlagsByModuleDict().get(module, []))

  def _GetKeyFlagsForModule(self, module):
   
    if not isinstance(module, str):
      module = module.__name__

    key_flags = self._GetFlagsDefinedByModule(module)

  
    for flag in self.KeyFlagsByModuleDict().get(module, []):
      if flag not in key_flags:
        key_flags.append(flag)
    return key_flags

  def AppendFlagValues(self, flag_values):
   
    for flag_name, flag in flag_values.FlagDict().iteritems():
      
      if flag_name == flag.name:
        self[flag_name] = flag

  def __setitem__(self, name, flag):
    """Registers a new flag variable."""
    fl = self.FlagDict()
    if not isinstance(flag, Flag):
      raise IllegalFlagValue(flag)
    if not isinstance(name, type("")):
      raise FlagsError("Flag name must be a string")
    if len(name) == 0:
      raise FlagsError("Flag name cannot be empty")
    
    if (fl.has_key(name) and not flag.allow_override and
        not fl[name].allow_override and not _RUNNING_PYCHECKER):
      raise DuplicateFlagError(name, self)
    short_name = flag.short_name
    if short_name is not None:
      if (fl.has_key(short_name) and not flag.allow_override and
          not fl[short_name].allow_override and not _RUNNING_PYCHECKER):
        raise DuplicateFlagError(short_name, self)
      fl[short_name] = flag
    fl[name] = flag
    global _exported_flags
    _exported_flags[name] = flag

  def __getitem__(self, name):
    """Retrieves the Flag object for the flag --name."""
    return self.FlagDict()[name]

  def __getattr__(self, name):
    """Retrieves the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    if not fl.has_key(name):
      raise AttributeError(name)
    return fl[name].value

  def __setattr__(self, name, value):
    """Sets the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    fl[name].value = value
    return value

  def _FlagIsRegistered(self, flag_obj):
    """Checks whether a Flag object is registered under some name.

    Note: this is non trivial: in addition to its normal name, a flag
    may have a short name too.  In self.FlagDict(), both the normal and
    the short name are mapped to the same flag object.  E.g., calling
    only "del FLAGS.short_name" is not unregistering the corresponding
    Flag object (it is still registered under the longer name).

    Args:
      flag_obj: A Flag object.

    Returns:
      A boolean: True iff flag_obj is registered under some name.
    """
    flag_dict = self.FlagDict()
    # Check whether flag_obj is registered under its long name.
    name = flag_obj.name
    if flag_dict.get(name, None) == flag_obj:
      return True
    # Check whether flag_obj is registered under its short name.
    short_name = flag_obj.short_name
    if (short_name is not None and
        flag_dict.get(short_name, None) == flag_obj):
      return True
    # The flag cannot be registered under any other name, so we do not
    # need to do a full search through the values of self.FlagDict().
    return False

  def __delattr__(self, flag_name):
    """Deletes a previously-defined flag from a flag object.

    This method makes sure we can delete a flag by using

      del flag_values_object.<flag_name>

    E.g.,

      flags.DEFINE_integer('foo', 1, 'Integer flag.')
      del flags.FLAGS.foo

    Args:
      flag_name: A string, the name of the flag to be deleted.

    Raises:
      AttributeError: When there is no registered flag named flag_name.
    """
    fl = self.FlagDict()
    if flag_name not in fl:
      raise AttributeError(flag_name)

    flag_obj = fl[flag_name]
    del fl[flag_name]

    if not self._FlagIsRegistered(flag_obj):
      # If the Flag object indicated by flag_name is no longer
      # registered (please see the docstring of _FlagIsRegistered), then
      # we delete the occurences of the flag object in all our internal
      # dictionaries.
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.KeyFlagsByModuleDict(), flag_obj)

  def __RemoveFlagFromDictByModule(self, flags_by_module_dict, flag_obj):
    """Removes a flag object from a module -> list of flags dictionary.

    Args:
      flags_by_module_dict: A dictionary that maps module names to lists of
        flags.
      flag_obj: A flag object.
    """
    for unused_module, flags_in_module in flags_by_module_dict.iteritems():
      # while (as opposed to if) takes care of multiple occurences of a
      # flag in the list for the same module.
      while flag_obj in flags_in_module:
        flags_in_module.remove(flag_obj)

  def SetDefault(self, name, value):
    """Changes the default value of the named flag object."""
    fl = self.FlagDict()
    if not fl.has_key(name):
      raise AttributeError(name)
    fl[name].SetDefault(value)

  def __contains__(self, name):
    """Returns True if name is a value (flag) in the dict."""
    return name in self.FlagDict()

  has_key = __contains__  # a synonym for __contains__()

  def __iter__(self):
    return self.FlagDict().iterkeys()

  # lhuang: my stealthy entry point
  def __call__(self, argv):
    try:
			# N.B.: return the rest of the command-line! (non-flag arguments)
      return self.__call2__(argv)
    except FlagsError, e:
        print 'Error: %s\nUsage: %s [flags]\n%s' % (e, list(argv)[0], FLAGS)
        sys.exit(1)


  # lhuang: external entry FLAGS(sys.argv) here
  def __call2__(self, argv):
    """Parses flags from argv; stores parsed flags into this FlagValues object.

    All unparsed arguments are returned.  Flags are parsed using the GNU
    Program Argument Syntax Conventions, using getopt:

    http://www.gnu.org/software/libc/manual/html_mono/libc.html#Getopt

    Args:
       argv: argument list. Can be of any type that may be converted to a list.

    Returns:
       The list of arguments not parsed as options, including argv[0]

    Raises:
       FlagsError: on any parsing error
    """
    # Support any sequence type that can be converted to a list
    argv = list(argv)

    shortopts = ""
    longopts = []

    fl = self.FlagDict()

    # This pre parses the argv list for --flagfile=<> options.
    argv = self.ReadFlagsFromFiles(argv)

    # Correct the argv to support the google style of passing boolean
    # parameters.  Boolean parameters may be passed by using --mybool,
    # --nomybool, --mybool=(true|false|1|0).  getopt does not support
    # having options that may or may not have a parameter.  We replace
    # instances of the short form --mybool and --nomybool with their
    # full forms: --mybool=(true|false).
    original_argv = list(argv)  # list() makes a copy
    shortest_matches = None
    for name, flag in fl.items():
      if not flag.boolean:
        continue
      if shortest_matches is None:
        # Determine the smallest allowable prefix for all flag names
        shortest_matches = self.ShortestUniquePrefixes(fl)
      no_name = 'no' + name
      prefix = shortest_matches[name]
      no_prefix = shortest_matches[no_name]

      # Replace all occurences of this boolean with extended forms
      for arg_idx in range(1, len(argv)):
        arg = argv[arg_idx]
        if arg.find('=') >= 0: continue
        if arg.startswith('--'+prefix) and ('--'+name).startswith(arg):
          argv[arg_idx] = ('--%s=true' % name)
        elif arg.startswith('--'+no_prefix) and ('--'+no_name).startswith(arg):
          argv[arg_idx] = ('--%s=false' % name)

    # Loop over all of the flags, building up the lists of short options
    # and long options that will be passed to getopt.  Short options are
    # specified as a string of letters, each letter followed by a colon
    # if it takes an argument.  Long options are stored in an array of
    # strings.  Each string ends with an '=' if it takes an argument.
    for name, flag in fl.items():
      longopts.append(name + "=")
      if len(name) == 1:  # one-letter option: allow short flag type also
        shortopts += name
        if not flag.boolean:
          shortopts += ":"

    longopts.append('undefok=')
    undefok_flags = []

    # In case --undefok is specified, loop to pick up unrecognized
    # options one by one.
    unrecognized_opts = []
    args = argv[1:]
    while True:
      try:
        optlist, unparsed_args = getopt.getopt(args, shortopts, longopts)
        break
      except getopt.GetoptError, e:
        if not e.opt or e.opt in fl:
          # Not an unrecognized option, reraise the exception as a FlagsError
          raise FlagsError(e)
        # Handle an unrecognized option.
        unrecognized_opts.append(e.opt)
        # Remove offender from args and try again
        for arg_index in range(len(args)):
          if ((args[arg_index] == '--' + e.opt) or
              (args[arg_index] == '-' + e.opt) or
              args[arg_index].startswith('--' + e.opt + '=')):
            args = args[0:arg_index] + args[arg_index+1:]
            break
        else:
          # We should have found the option, so we don't expect to get
          # here.  We could assert, but raising the original exception
          # might work better.
          raise FlagsError(e)

    for name, arg in optlist:
      if name == '--undefok':
        flag_names = arg.split(',')
        undefok_flags.extend(flag_names)
        # For boolean flags, if --undefok=boolflag is specified, then we should
        # also accept --noboolflag, in addition to --boolflag.
        # Since we don't know the type of the undefok'd flag, this will affect
        # non-boolean flags as well.
        # NOTE: You shouldn't use --undefok=noboolflag, because then we will
        # accept --nonoboolflag here.  We are choosing not to do the conversion
        # from noboolflag -> boolflag because of the ambiguity that flag names
        # can start with 'no'.
        undefok_flags.extend('no' + name for name in flag_names)
        continue
      if name.startswith('--'):
        # long option
        name = name[2:]
        short_option = 0
      else:
        # short option
        name = name[1:]
        short_option = 1
      if fl.has_key(name):
        flag = fl[name]
        if flag.boolean and short_option: arg = 1
        flag.Parse(arg)

    # If there were unrecognized options, raise an exception unless
    # the options were named via --undefok.
    for opt in unrecognized_opts:
      if opt not in undefok_flags:
        raise UnrecognizedFlagError(opt)

    if unparsed_args:
      # unparsed_args becomes the first non-flag detected by getopt to
      # the end of argv.  Because argv may have been modified above,
      # return original_argv for this region.
      return argv[:1] + original_argv[-len(unparsed_args):]
    else:
      return argv[:1]

  def Reset(self):
    """Resets the values to the point before FLAGS(argv) was called."""
    for f in self.FlagDict().values():
      f.Unparse()

  def RegisteredFlags(self):
    """Returns: a list of the names and short names of all registered flags."""
    return self.FlagDict().keys()

  def FlagValuesDict(self):
    """Returns: a dictionary that maps flag names to flag values."""
    flag_values = {}

    for flag_name in self.RegisteredFlags():
      flag = self.FlagDict()[flag_name]
      flag_values[flag_name] = flag.value

    return flag_values

  def __str__(self):
    """Generates a help string for all known flags."""
    return self.GetHelp()

  def GetHelp(self, prefix=''):
    """Generates a help string for all known flags."""
    helplist = []

    flags_by_module = self.FlagsByModuleDict()
    if flags_by_module:

      modules = flags_by_module.keys()
      modules.sort()

      # Print the help for the main module first, if possible.
      main_module = _GetMainModule()
      if main_module in modules:
        modules.remove(main_module)
        modules = [main_module] + modules

      for module in modules:
        self.__RenderOurModuleFlags(module, helplist)

      self.__RenderModuleFlags('gflags',
                               _SPECIAL_FLAGS.FlagDict().values(),
                               helplist)

    else:
      # Just print one long list of flags.
      self.__RenderFlagList(
          self.FlagDict().values() + _SPECIAL_FLAGS.FlagDict().values(),
          helplist, prefix)

    return '\n'.join(helplist)

  def __RenderModuleFlags(self, module, flags, output_lines, prefix=""):
    """Generates a help string for a given module."""
    output_lines.append('\n%s%s:' % (prefix, module))
    self.__RenderFlagList(flags, output_lines, prefix + "  ")

  def __RenderOurModuleFlags(self, module, output_lines, prefix=""):
    """Generates a help string for a given module."""
    flags = self._GetFlagsDefinedByModule(module)
    if flags:
      self.__RenderModuleFlags(module, flags, output_lines, prefix)

  def __RenderOurModuleKeyFlags(self, module, output_lines, prefix=""):
    """Generates a help string for the key flags of a given module.

    Args:
      module: A module object or a module name (a string).
      output_lines: A list of strings.  The generated help message
        lines will be appended to this list.
      prefix: A string that is prepended to each generated help line.
    """
    key_flags = self._GetKeyFlagsForModule(module)
    if key_flags:
      self.__RenderModuleFlags(module, key_flags, output_lines, prefix)

  def MainModuleHelp(self):
    """Returns: A string describing the key flags of the main module."""
    helplist = []
    self.__RenderOurModuleKeyFlags(_GetMainModule(), helplist)
    return '\n'.join(helplist)

  def __RenderFlagList(self, flaglist, output_lines, prefix="  "):
    fl = self.FlagDict()
    special_fl = _SPECIAL_FLAGS.FlagDict()
    flaglist = [(flag.name, flag) for flag in flaglist]
    flaglist.sort()
    flagset = {}
    for (name, flag) in flaglist:
      # It's possible this flag got deleted or overridden since being
      # registered in the per-module flaglist.  Check now against the
      # canonical source of current flag information, the FlagDict.
      if fl.get(name, None) != flag and special_fl.get(name, None) != flag:
        # a different flag is using this name now
        continue
      # only print help once
      if flagset.has_key(flag): continue
      flagset[flag] = 1
      flaghelp = ""
      # lhuang:
      if flag.name in ["help", "helpshort"]:
			  continue
			
      if flag.short_name:
        flaghelp += "-" if len(flag.short_name) == 1 else "--"  # lhuang: shortname can be long
        flaghelp += "%s," % flag.short_name
      if flag.boolean:
        flaghelp += "--[no]%s" % flag.name + ":"
      else:
        flaghelp += "--%s" % flag.name + ":"
      flaghelp += "  "
      if flag.help:
        flaghelp += flag.help
      flaghelp = TextWrap(flaghelp, indent=prefix+"  ",
                          firstline_indent=prefix)
      if flag.default_as_str:
        flaghelp += "\n" # lhuang
        flaghelp += TextWrap("(default: %s)" % flag.default_as_str,
                             indent=prefix+"  ")
      if flag.parser.syntactic_help:
        flaghelp += "\t" # lhuang
        flaghelp += TextWrap("(%s)" % flag.parser.syntactic_help,
                             indent=prefix+"  ")
      output_lines.append(flaghelp)

  def get(self, name, default):
    """Returns the value of a flag (if not None) or a default value.

    Args:
      name: A string, the name of a flag.
      default: Default value to use if the flag value is None.
    """

    value = self.__getattr__(name)
    if value is not None:  # Can't do if not value, b/c value might be '0' or ""
      return value
    else:
      return default

  def ShortestUniquePrefixes(self, fl):
    """Returns: dictionary; maps flag names to their shortest unique prefix."""
    # Sort the list of flag names
    sorted_flags = []
    for name, flag in fl.items():
      sorted_flags.append(name)
      if flag.boolean:
        sorted_flags.append('no%s' % name)
    sorted_flags.sort()

    # For each name in the sorted list, determine the shortest unique
    # prefix by comparing itself to the next name and to the previous
    # name (the latter check uses cached info from the previous loop).
    shortest_matches = {}
    prev_idx = 0
    for flag_idx in range(len(sorted_flags)):
      curr = sorted_flags[flag_idx]
      if flag_idx == (len(sorted_flags) - 1):
        next = None
      else:
        next = sorted_flags[flag_idx+1]
        next_len = len(next)
      for curr_idx in range(len(curr)):
        if (next is None
            or curr_idx >= next_len
            or curr[curr_idx] != next[curr_idx]):
          # curr longer than next or no more chars in common
          shortest_matches[curr] = curr[:max(prev_idx, curr_idx) + 1]
          prev_idx = curr_idx
          break
      else:
        # curr shorter than (or equal to) next
        shortest_matches[curr] = curr
        prev_idx = curr_idx + 1  # next will need at least one more char
    return shortest_matches

  def __IsFlagFileDirective(self, flag_string):
    """Checks whether flag_string contain a --flagfile=<foo> directive."""
    if isinstance(flag_string, type("")):
      if flag_string.startswith('--flagfile='):
        return 1
      elif flag_string == '--flagfile':
        return 1
      elif flag_string.startswith('-flagfile='):
        return 1
      elif flag_string == '-flagfile':
        return 1
      else:
        return 0
    return 0

  def ExtractFilename(self, flagfile_str):
    """Returns filename from a flagfile_str of form -[-]flagfile=filename.

    The cases of --flagfile foo and -flagfile foo shouldn't be hitting
    this function, as they are dealt with in the level above this
    function.
    """
    if flagfile_str.startswith('--flagfile='):
      return os.path.expanduser((flagfile_str[(len('--flagfile=')):]).strip())
    elif flagfile_str.startswith('-flagfile='):
      return os.path.expanduser((flagfile_str[(len('-flagfile=')):]).strip())
    else:
      raise FlagsError('Hit illegal --flagfile type: %s' % flagfile_str)

  def __GetFlagFileLines(self, filename, parsed_file_list):
    """Returns the useful (!=comments, etc) lines from a file with flags.

    Args:
      filename: A string, the name of the flag file.
      parsed_file_list: A list of the names of the files we have
        already read.  MUTATED BY THIS FUNCTION.

    Returns:
      List of strings. See the note below.

    NOTE(springer): This function checks for a nested --flagfile=<foo>
    tag and handles the lower file recursively. It returns a list of
    all the lines that _could_ contain command flags. This is
    EVERYTHING except whitespace lines and comments (lines starting
    with '#' or '//').
    """
    line_list = []  # All line from flagfile.
    flag_line_list = []  # Subset of lines w/o comments, blanks, flagfile= tags.
    try:
      file_obj = open(filename, 'r')
    except IOError, e_msg:
      print e_msg
      print 'ERROR:: Unable to open flagfile: %s' % (filename)
      return flag_line_list

    line_list = file_obj.readlines()
    file_obj.close()
    parsed_file_list.append(filename)

    # This is where we check each line in the file we just read.
    for line in line_list:
      if line.isspace():
        pass
      # Checks for comment (a line that starts with '#').
      elif line.startswith('#') or line.startswith('//'):
        pass
      # Checks for a nested "--flagfile=<bar>" flag in the current file.
      # If we find one, recursively parse down into that file.
      elif self.__IsFlagFileDirective(line):
        sub_filename = self.ExtractFilename(line)
        # We do a little safety check for reparsing a file we've already done.
        if not sub_filename in parsed_file_list:
          included_flags = self.__GetFlagFileLines(sub_filename,
                                                   parsed_file_list)
          flag_line_list.extend(included_flags)
        else:  # Case of hitting a circularly included file.
          print >>sys.stderr, ('Warning: Hit circular flagfile dependency: %s'
                               % sub_filename)
      else:
        # Any line that's not a comment or a nested flagfile should get
        # copied into 2nd position.  This leaves earlier arguements
        # further back in the list, thus giving them higher priority.
        flag_line_list.append(line.strip())
    return flag_line_list

  def ReadFlagsFromFiles(self, argv):
    """Processes command line args, but also allow args to be read from file.
    Args:
      argv: A list of strings, usually sys.argv, which may contain one
        or more flagfile directives of the form --flagfile="./filename".

    Returns:

      A new list which has the original list combined with what we read
      from any flagfile(s).

    References: Global gflags.FLAG class instance.

    This function should be called before the normal FLAGS(argv) call.
    This function scans the input list for a flag that looks like:
    --flagfile=<somefile>. Then it opens <somefile>, reads all valid key
    and value pairs and inserts them into the input list between the
    first item of the list and any subsequent items in the list.

    Note that your application's flags are still defined the usual way
    using gflags DEFINE_flag() type functions.

    Notes (assuming we're getting a commandline of some sort as our input):
    --> Flags from the command line argv _should_ always take precedence!
    --> A further "--flagfile=<otherfile.cfg>" CAN be nested in a flagfile.
        It will be processed after the parent flag file is done.
    --> For duplicate flags, first one we hit should "win".
    --> In a flagfile, a line beginning with # or // is a comment.
    --> Entirely blank lines _should_ be ignored.
    """
    parsed_file_list = []
    rest_of_args = argv
    new_argv = []
    while rest_of_args:
      current_arg = rest_of_args[0]
      rest_of_args = rest_of_args[1:]
      if self.__IsFlagFileDirective(current_arg):
        # This handles the case of -(-)flagfile foo.  In this case the
        # next arg really is part of this one.
        if current_arg == '--flagfile' or current_arg == '-flagfile':
          if not rest_of_args:
            raise IllegalFlagValue('--flagfile with no argument')
          flag_filename = os.path.expanduser(rest_of_args[0])
          rest_of_args = rest_of_args[1:]
        else:
          # This handles the case of (-)-flagfile=foo.
          flag_filename = self.ExtractFilename(current_arg)
        new_argv = (new_argv[:1] +
                    self.__GetFlagFileLines(flag_filename, parsed_file_list) +
                    new_argv[1:])
      else:
        new_argv.append(current_arg)

    return new_argv

  def FlagsIntoString(self):
    """Returns a string with the flags assignments from this FlagValues object.

    This function ignores flags whose value is None.  Each flag
    assignment is separated by a newline.

    NOTE: MUST mirror the behavior of the C++ function
    CommandlineFlagsIntoString from google3/base/commandlineflags.cc.
    """
    s = ''
    for flag in self.FlagDict().values():
      if flag.value is not None:
        s += flag.Serialize() + '\n'
    return s

  def AppendFlagsIntoFile(self, filename):
    """Appends all flags assignments from this FlagInfo object to a file.

    Output will be in the format of a flagfile.

    NOTE: MUST mirror the behavior of the C++ version of
    AppendFlagsIntoFile from google3/base/commandlineflags.cc.
    """
    out_file = open(filename, 'a')
    out_file.write(self.FlagsIntoString())
    out_file.close()

  def WriteHelpInXMLFormat(self, outfile=None):
    """Outputs flag documentation in XML format.

    NOTE: We use element names that are consistent with those used by
    the C++ command-line flag library, from
    google3/base/commandlineflags_reporting.cc.  We also use a few new
    elements (e.g., <key>), but we do not interfere / overlap with
    existing XML elements used by the C++ library.  Please maintain this
    consistency.

    Args:
      outfile: File object we write to.  Default None means sys.stdout.
    """
    outfile = outfile or sys.stdout

    outfile.write('<?xml version=\"1.0\"?>\n')
    outfile.write('<AllFlags>\n')
    indent = '  '
    _WriteSimpleXMLElement(outfile, 'program', os.path.basename(sys.argv[0]),
                           indent)

    usage_doc = sys.modules['__main__'].__doc__
    if not usage_doc:
      usage_doc = '\nUSAGE: %s [flags]\n' % sys.argv[0]
    else:
      usage_doc = usage_doc.replace('%s', sys.argv[0])
    _WriteSimpleXMLElement(outfile, 'usage', usage_doc, indent)

    # Get list of key flags for the main module.
    key_flags = self._GetKeyFlagsForModule(_GetMainModule())

    # Sort flags by declaring module name and next by flag name.
    flags_by_module = self.FlagsByModuleDict()
    all_module_names = list(flags_by_module.keys())
    all_module_names.sort()
    for module_name in all_module_names:
      flag_list = [(f.name, f) for f in flags_by_module[module_name]]
      flag_list.sort()
      for unused_flag_name, flag in flag_list:
        is_key = flag in key_flags
        flag.WriteInfoInXMLFormat(outfile, module_name,
                                  is_key=is_key, indent=indent)

    outfile.write('</AllFlags>\n')
    outfile.flush()
# end of FlagValues definition


# The global FlagValues instance //lhuang
FLAGS = FlagValues()


def _MakeXMLSafe(s):
  """Escapes <, >, and & from s, and removes XML 1.0-illegal chars."""
  s = cgi.escape(s)  # Escape <, >, and &
  # Remove characters that cannot appear in an XML 1.0 document
  # (http://www.w3.org/TR/REC-xml/#charsets).
  #
  # NOTE: if there are problems with current solution, one may move to
  # XML 1.1, which allows such chars, if they're entity-escaped (&#xHH;).
  s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
  return s


def _WriteSimpleXMLElement(outfile, name, value, indent):
  """Writes a simple XML element.

  Args:
    outfile: File object we write the XML element to.
    name: A string, the name of XML element.
    value: A Python object, whose string representation will be used
      as the value of the XML element.
    indent: A string, prepended to each line of generated output.
  """
  value_str = str(value)
  if isinstance(value, bool):
    # Display boolean values as the C++ flag library does: no caps.
    value_str = value_str.lower()
  outfile.write('%s<%s>%s</%s>\n' %
                (indent, name, _MakeXMLSafe(value_str), name))


class Flag:
  """Information about a command-line flag.

  'Flag' objects define the following fields:
    .name  - the name for this flag
    .default - the default value for this flag
    .default_as_str - default value as repr'd string, e.g., "'true'" (or None)
    .value  - the most recent parsed value of this flag; set by Parse()
    .help  - a help string or None if no help is available
    .short_name  - the single letter alias for this flag (or None)
    .boolean  - if 'true', this flag does not accept arguments
    .present  - true if this flag was parsed from command line flags.
    .parser  - an ArgumentParser object
    .serializer - an ArgumentSerializer object
    .allow_override - the flag may be redefined without raising an error

  The only public method of a 'Flag' object is Parse(), but it is
  typically only called by a 'FlagValues' object.  The Parse() method is
  a thin wrapper around the 'ArgumentParser' Parse() method.  The parsed
  value is saved in .value, and the .present attribute is updated.  If
  this flag was already present, a FlagsError is raised.

  Parse() is also called during __init__ to parse the default value and
  initialize the .value attribute.  This enables other python modules to
  safely use flags even if the __main__ module neglects to parse the
  command line arguments.  The .present attribute is cleared after
  __init__ parsing.  If the default value is set to None, then the
  __init__ parsing step is skipped and the .value attribute is
  initialized to None.

  Note: The default value is also presented to the user in the help
  string, so it is important that it be a legal value for this flag.
  """

  def __init__(self, parser, serializer, name, default, help_string,
               short_name=None, boolean=0, allow_override=0):
    self.name = name

    if not help_string:
      help_string = '(no help available)'

    self.help = help_string
    self.short_name = short_name
    self.boolean = boolean
    self.present = 0
    self.parser = parser
    self.serializer = serializer
    self.allow_override = allow_override
    self.value = None

    self.SetDefault(default)

  def __GetParsedValueAsString(self, value):
    if value is None:
      return None
    if self.serializer:
      return repr(self.serializer.Serialize(value))
    if self.boolean:
      if value:
        return repr('true')
      else:
        return repr('false')
    return repr(str(value))

  def Parse(self, argument):
    try:
      self.value = self.parser.Parse(argument)
    except ValueError, e:  # recast ValueError as IllegalFlagValue
      raise IllegalFlagValue("flag --%s: %s" % (self.name, e))
    self.present += 1

  def Unparse(self):
    if self.default is None:
      self.value = None
    else:
      self.Parse(self.default)
    self.present = 0

  def Serialize(self):
    if self.value is None:
      return ''
    if self.boolean:
      if self.value:
        return "--%s" % self.name
      else:
        return "--no%s" % self.name
    else:
      if not self.serializer:
        raise FlagsError("Serializer not present for flag %s" % self.name)
      return "--%s=%s" % (self.name, self.serializer.Serialize(self.value))

  def SetDefault(self, value):
    """Changes the default value (and current value too) for this Flag."""
    # We can't allow a None override because it may end up not being
    # passed to C++ code when we're overriding C++ flags.  So we
    # cowardly bail out until someone fixes the semantics of trying to
    # pass None to a C++ flag.  See swig_flags.Init() for details on
    # this behavior.
    if value is None and self.allow_override:
      raise DuplicateFlag(self.name)

    self.default = value
    self.Unparse()
    self.default_as_str = self.__GetParsedValueAsString(self.value)

  def Type(self):
    """Returns: a string that describes the type of this Flag."""
    # NOTE: we use strings, and not the types.*Type constants because
    # our flags can have more exotic types, e.g., 'comma separated list
    # of strings', 'whitespace separated list of strings', etc.
    return self.parser.Type()

  def WriteInfoInXMLFormat(self, outfile, module_name, is_key=False, indent=''):
    """Writes common info about this flag, in XML format.

    This is information that is relevant to all flags (e.g., name,
    meaning, etc.).  If you defined a flag that has some other pieces of
    info, then please override _WriteCustomInfoInXMLFormat.

    Please do NOT override this method.

    Args:
      outfile: File object we write to.
      module_name: A string, the name of the module that defines this flag.
      is_key: A boolean, True iff this flag is key for main module.
      indent: A string that is prepended to each generated line.
    """
    outfile.write(indent + '<flag>\n')
    inner_indent = indent + '  '
    if is_key:
      _WriteSimpleXMLElement(outfile, 'key', 'yes', inner_indent)
    _WriteSimpleXMLElement(outfile, 'file', module_name, inner_indent)
    # Print flag features that are relevant for all flags.
    _WriteSimpleXMLElement(outfile, 'name', self.name, inner_indent)
    if self.short_name:
      _WriteSimpleXMLElement(outfile, 'short_name', self.short_name,
                             inner_indent)
    if self.help:
      _WriteSimpleXMLElement(outfile, 'meaning', self.help, inner_indent)
    _WriteSimpleXMLElement(outfile, 'default', self.default, inner_indent)
    _WriteSimpleXMLElement(outfile, 'current', self.value, inner_indent)
    _WriteSimpleXMLElement(outfile, 'type', self.Type(), inner_indent)
    # Print extra flag features this flag may have.
    self._WriteCustomInfoInXMLFormat(outfile, inner_indent)
    outfile.write(indent + '</flag>\n')

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    """Writes extra info about this flag, in XML format.

    "Extra" means "not already printed by WriteInfoInXMLFormat above."

    Args:
      outfile: File object we write to.
      indent: A string that is prepended to each generated line.
    """
    # Usually, the parser knows the extra details about the flag, so
    # we just forward the call to it.
    self.parser.WriteCustomInfoInXMLFormat(outfile, indent)
# End of Flag definition


class ArgumentParser:
  """Base class used to parse and convert arguments.

  The Parse() method checks to make sure that the string argument is a
  legal value and convert it to a native type.  If the value cannot be
  converted, it should throw a 'ValueError' exception with a human
  readable explanation of why the value is illegal.

  Subclasses should also define a syntactic_help string which may be
  presented to the user to describe the form of the legal values.
  """
  syntactic_help = ""

  def Parse(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

  def Type(self):
    return 'string'

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    pass


class ArgumentSerializer:
  """Base class for generating string representations of a flag value."""

  def Serialize(self, value):
    return str(value)


class ListSerializer(ArgumentSerializer):

  def __init__(self, list_sep):
    self.list_sep = list_sep

  def Serialize(self, value):
    return self.list_sep.join([str(x) for x in value])


# The DEFINE functions are explained in mode details in the module doc string.


def DEFINE(parser, name, default, help, flag_values=FLAGS, serializer=None,
           **args):
  """Registers a generic Flag object.

  NOTE: in the docstrings of all DEFINE* functions, "registers" is short
  for "creates a new flag and registers it".

  Auxiliary function: clients should use the specialized DEFINE_<type>
  function instead.

  Args:
    parser: ArgumentParser that is used to parse the flag arguments.
    name: A string, the flag name.
    default: The default value of the flag.
    help: A help string.
    flag_values: FlagValues object the flag will be registered with.
    serializer: ArgumentSerializer that serializes the flag value.
    args: Dictionary with extra keyword args that are passes to the
      Flag __init__.
  """
  DEFINE_flag(Flag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_flag(flag, flag_values=FLAGS):
  """Registers a 'Flag' object with a 'FlagValues' object.

  By default, the global FLAGS 'FlagValue' object is used.

  Typical users will use one of the more specialized DEFINE_xxx
  functions, such as DEFINE_string or DEFINE_integer.  But developers
  who need to create Flag objects themselves should use this function
  to register their flags.
  """
  # copying the reference to flag_values prevents pychecker warnings
  fv = flag_values
  fv[flag.name] = flag
  # Tell flag_values who's defining the flag.
  if isinstance(flag_values, FlagValues):
    # Regarding the above isinstance test: some users pass funny
    # values of flag_values (e.g., {}) in order to avoid the flag
    # registration (in the past, there used to be a flag_values ==
    # FLAGS test here) and redefine flags with the same name (e.g.,
    # debug).  To avoid breaking their code, we perform the
    # registration only if flag_values is a real FlagValues object.
    flag_values._RegisterFlagByModule(_GetCallingModule(), flag)


def _InternalDeclareKeyFlags(flag_names, flag_values=FLAGS):
  """Declares a flag as key for the calling module.

  Internal function.  User code should call DECLARE_key_flag or
  ADOPT_module_key_flags instead.

  Args:
    flag_names: A list of strings that are names of already-registered
      Flag objects.
    flag_values: A FlagValue object.  This should almost never need
      to be overridden.

  Raises:
    UnrecognizedFlagError: when we refer to a flag that was not
      defined yet.
  """
  module = _GetCallingModule()

  for flag_name in flag_names:
    if flag_name not in flag_values:
      raise UnrecognizedFlagError(flag_name)
    flag = flag_values.FlagDict()[flag_name]
    flag_values._RegisterKeyFlagForModule(module, flag)


def DECLARE_key_flag(flag_name, flag_values=FLAGS):
  """Declares one flag as key to the current module.

  Key flags are flags that are deemed really important for a module.
  They are important when listing help messages; e.g., if the
  --helpshort command-line flag is used, then only the key flags of the
  main module are listed (instead of all flags, as in the case of
  --help).

  Sample usage:

    flags.DECLARED_key_flag('flag_1')

  Args:
    flag_name: A string, the name of an already declared flag.
      (Redeclaring flags as key, including flags implicitly key
      because they were declared in this module, is a no-op.)
    flag_values: A FlagValues object.  This should almost never
      need to be overridden.
  """
  _InternalDeclareKeyFlags([flag_name], flag_values=flag_values)


def ADOPT_module_key_flags(module, flag_values=FLAGS):
  """Declares that all flags key to a module are key to the current module.

  Args:
    module: A module object.
    flag_values: A FlagValues object.  This should almost never need
      to be overridden.

  Raises:
    FlagsError: When given an argument that is a module name (a
    string), instead of a module object.
  """
  # NOTE(salcianu): an even better test would be if not
  # isinstance(module, types.ModuleType) but I didn't want to import
  # types for such a tiny use.
  if isinstance(module, str):
    raise FlagsError('Received module name %s; expected a module object.'
                     % module)
  _InternalDeclareKeyFlags(
      [f.name for f in flag_values._GetKeyFlagsForModule(module.__name__)],
      flag_values=flag_values)


#
# STRING FLAGS
#


def DEFINE_string(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be any string."""
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# BOOLEAN FLAGS
#
# and the special HELP flags.

class BooleanParser(ArgumentParser):
  """Parser of boolean values."""

  def Convert(self, argument):
    """Converts the argument to a boolean; raise ValueError on errors."""
    if type(argument) == str:
      if argument.lower() in ['true', 't', '1']:
        return True
      elif argument.lower() in ['false', 'f', '0']:
        return False

    bool_argument = bool(argument)
    if argument == bool_argument:
      # The argument is a valid boolean (True, False, 0, or 1), and not just
      # something that always converts to bool (list, string, int, etc.).
      return bool_argument

    raise ValueError('Non-boolean argument to boolean flag', argument)

  def Parse(self, argument):
    val = self.Convert(argument)
    return val

  def Type(self):
    return 'bool'


class BooleanFlag(Flag):
  """Basic boolean flag.

  Boolean flags do not take any arguments, and their value is either
  True (1) or False (0).  The false value is specified on the command
  line by prepending the word 'no' to either the long or the short flag
  name.

  For example, if a Boolean flag was created whose long name was
  'update' and whose short name was 'x', then this flag could be
  explicitly unset through either --noupdate or --nox.
  """

  def __init__(self, name, default, help, short_name=None, **args):
    p = BooleanParser()
    Flag.__init__(self, p, None, name, default, help, short_name, 1, **args)
    if not self.help: self.help = "a boolean value"


def DEFINE_boolean(name, default, help, flag_values=FLAGS, **args):
  """Registers a boolean flag.

  Such a boolean flag does not take an argument.  If a user wants to
  specify a false value explicitly, the long option beginning with 'no'
  must be used: i.e. --noflag

  This flag will have a value of None, True or False.  None is possible
  if default=None and the user does not specify the flag on the command
  line.
  """
  DEFINE_flag(BooleanFlag(name, default, help, **args), flag_values)

# Match C++ API to unconfuse C++ people.
DEFINE_bool = DEFINE_boolean

class HelpFlag(BooleanFlag):
  """
  HelpFlag is a special boolean flag that prints usage information and
  raises a SystemExit exception if it is ever found in the command
  line arguments.  Note this is called with allow_override=1, so other
  apps can define their own --help flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "help", 0, "show this help",
                         short_name="?", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = str(FLAGS)
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)


class HelpXMLFlag(BooleanFlag):
  """Similar to HelpFlag, but generates output in XML format."""

  def __init__(self):
    BooleanFlag.__init__(self, 'helpxml', False,
                         'like --help, but generates XML output',
                         allow_override=1)

  def Parse(self, arg):
    if arg:
      FLAGS.WriteHelpInXMLFormat(sys.stdout)
      sys.exit(1)


class HelpshortFlag(BooleanFlag):
  """
  HelpshortFlag is a special boolean flag that prints usage
  information for the "main" module, and rasies a SystemExit exception
  if it is ever found in the command line arguments.  Note this is
  called with allow_override=1, so other apps can define their own
  --helpshort flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "helpshort", 0,
                         "show usage only for this module", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = FLAGS.MainModuleHelp()
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)


#
# FLOAT FLAGS
#

class FloatParser(ArgumentParser):
  """Parser of floating point values.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "a"
  number_name = "number"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound != None and upper_bound != None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 1:
      sh = "a positive %s" % self.number_name
    elif upper_bound == -1:
      sh = "a negative %s" % self.number_name
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound != None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound != None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    """Converts argument to a float; raises ValueError on errors."""
    return float(argument)

  def Parse(self, argument):
    val = self.Convert(argument)
    if ((self.lower_bound != None and val < self.lower_bound) or
        (self.upper_bound != None and val > self.upper_bound)):
      raise ValueError("%s is not %s" % (val, self.syntactic_help))
    return val

  def Type(self):
    return 'float'

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    if self.lower_bound is not None:
      _WriteSimpleXMLElement(outfile, 'lower_bound', self.lower_bound, indent)
    if self.upper_bound is not None:
      _WriteSimpleXMLElement(outfile, 'upper_bound', self.upper_bound, indent)
# End of FloatParser


def DEFINE_float(name, default, help, lower_bound=None, upper_bound=None,
                 flag_values=FLAGS, **args):
  """Registers a flag whose value must be a float.

  If lower_bound or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# INTEGER FLAGS
#


class IntegerParser(FloatParser):
  """Parser of an integer value.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "an"
  number_name = "integer"
  syntactic_help = " ".join((number_article, number_name))

  def Convert(self, argument):
    __pychecker__ = 'no-returnvalues'
    if type(argument) == str:
      base = 10
      if len(argument) > 2 and argument[0] == "0" and argument[1] == "x":
        base = 16
      try:
        return int(argument, base)
      # ValueError is thrown when argument is a string, and overflows an int.
      except ValueError:
        return long(argument, base)
    else:
      try:
        return int(argument)
      # OverflowError is thrown when argument is numeric, and overflows an int.
      except OverflowError:
        return long(argument)

  def Type(self):
    return 'int'


def DEFINE_integer(name, default, help, lower_bound=None, upper_bound=None,
                   flag_values=FLAGS, **args):
  """Registers a flag whose value must be an integer.

  If lower_bound, or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# ENUM FLAGS
#


class EnumParser(ArgumentParser):
  """Parser of a string enum value (a string value from a given set).

  If enum_values (see below) is not specified, any string is allowed.
  """

  def __init__(self, enum_values=None):
    self.enum_values = enum_values

  def Parse(self, argument):
    if self.enum_values and argument not in self.enum_values:
      raise ValueError("value should be one of <%s>" %
                       "|".join(self.enum_values))
    return argument

  def Type(self):
    return 'string enum'


class EnumFlag(Flag):
  """Basic enum flag; its value can be any string from list of enum_values."""

  def __init__(self, name, default, help, enum_values=None,
               short_name=None, **args):
    enum_values = enum_values or []
    p = EnumParser(enum_values)
    g = ArgumentSerializer()
    Flag.__init__(self, p, g, name, default, help, short_name, **args)
    if not self.help: self.help = "an enum string"
    self.help = "<%s>: %s" % ("|".join(enum_values), self.help)

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    for enum_value in self.parser.enum_values:
      _WriteSimpleXMLElement(outfile, 'enum_value', enum_value, indent)


def DEFINE_enum(name, default, enum_values, help, flag_values=FLAGS,
                **args):
  """Registers a flag whose value can be any string from enum_values."""
  DEFINE_flag(EnumFlag(name, default, help, enum_values, ** args),
              flag_values)


#
# LIST FLAGS
#


class BaseListParser(ArgumentParser):
  """Base class for a parser of lists of strings.

  To extend, inherit from this class; from the subclass __init__, call

    BaseListParser.__init__(self, token, name)

  where token is a character used to tokenize, and name is a description
  of the separator.
  """

  def __init__(self, token=None, name=None):
    assert name
    self._token = token
    self._name = name
    self.syntactic_help = "a %s separated list" % self._name

  def Parse(self, argument):
    if argument == '':
      return []
    else:
      return [s.strip() for s in argument.split(self._token)]

  def Type(self):
    return '%s separated list of strings' % self._name


class ListParser(BaseListParser):
  """Parser for a comma-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, ',', 'comma')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    _WriteSimpleXMLElement(outfile, 'list_separator', repr(','), indent)


class WhitespaceSeparatedListParser(BaseListParser):
  """Parser for a whitespace-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, None, 'whitespace')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    separators = list(string.whitespace)
    separators.sort()
    for ws_char in string.whitespace:
      _WriteSimpleXMLElement(outfile, 'list_separator', repr(ws_char), indent)


def DEFINE_list(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a comma-separated list of strings."""
  parser = ListParser()
  serializer = ListSerializer(',')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


def DEFINE_spaceseplist(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a whitespace-separated list of strings.

  Any whitespace can be used as a separator.
  """
  parser = WhitespaceSeparatedListParser()
  serializer = ListSerializer(' ')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# MULTI FLAGS
#


class MultiFlag(Flag):
  """A flag that can appear multiple time on the command-line.

  The value of such a flag is a list that contains the individual values
  from all the appearances of that flag on the command-line.

  See the __doc__ for Flag for most behavior of this class.  Only
  differences in behavior are described here:

    * The default value may be either a single value or a list of values.
      A single value is interpreted as the [value] singleton list.

    * The value of the flag is always a list, even if the option was
      only supplied once, and even if the default value is a single
      value
  """

  def __init__(self, *args, **kwargs):
    Flag.__init__(self, *args, **kwargs)
    self.help += ';\n    repeat this option to specify a list of values'

  def Parse(self, arguments):
    """Parses one or more arguments with the installed parser.

    Args:
      arguments: a single argument or a list of arguments (typically a
        list of default values); a single argument is converted
        internally into a list containing one item.
    """
    if not isinstance(arguments, list):
      # Default value may be a list of values.  Most other arguments
      # will not be, so convert them into a single-item list to make
      # processing simpler below.
      arguments = [arguments]

    if self.present:
      # keep a backup reference to list of previously supplied option values
      values = self.value
    else:
      # "erase" the defaults with an empty list
      values = []

    for item in arguments:
      # have Flag superclass parse argument, overwriting self.value reference
      Flag.Parse(self, item)  # also increments self.present
      values.append(self.value)

    # put list of option values back in the 'value' attribute
    self.value = values

  def Serialize(self):
    if not self.serializer:
      raise FlagsError("Serializer not present for flag %s" % self.name)
    if self.value is None:
      return ''

    s = ''

    multi_value = self.value

    for self.value in multi_value:
      if s: s += ' '
      s += Flag.Serialize(self)

    self.value = multi_value

    return s

  def Type(self):
    return 'multi ' + self.parser.Type()


def DEFINE_multi(parser, serializer, name, default, help, flag_values=FLAGS,
                 **args):
  """Registers a generic MultiFlag that parses its args with a given parser.

  Auxiliary function.  Normal users should NOT use it directly.

  Developers who need to create their own 'Parser' classes for options
  which can appear multiple times can call this module function to
  register their flags.
  """
  DEFINE_flag(MultiFlag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_multistring(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of any strings.

  Use the flag on the command line multiple times to place multiple
  string values into the list.  The 'default' may be a single string
  (which will be converted into a single-element list) or a list of
  strings.
  """
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_int(name, default, help, lower_bound=None, upper_bound=None,
                     flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary integers.

  Use the flag on the command line multiple times to place multiple
  integer values into the list.  The 'default' may be a single integer
  (which will be converted into a single-element list) or a list of
  integers.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


# Now register the flags that we want to exist in all applications.
# These are all defined with allow_override=1, so user-apps can use
# these flagnames for their own purposes, if they want.
DEFINE_flag(HelpFlag())
DEFINE_flag(HelpshortFlag())

# lhuang
#DEFINE_flag(HelpXMLFlag())

# Define special flags here so that help may be generated for them.
_SPECIAL_FLAGS = FlagValues()

