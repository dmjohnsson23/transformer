from html import escape

class FieldRenderer:
    """
    Used to render HTML inputs in the output HTML. Subclass to output the inputs in various different template formats (e.g. Jinja, PHP, etc...).
    """
    _renderer_type = None
    type: str
    name: str
    label: str
    style: dict

    @classmethod
    def set_render_type(cls, renderer):
        if not issubclass(renderer, cls):
            raise TypeError('Renderer type must be a subclass of FieldRenderer')
        cls._renderer_type = renderer
    
    @classmethod
    def make(cls, type):
        renderer = (cls._renderer_type or cls)()
        renderer.type = type
        return renderer

    def render(self):
        if self.type == 'button':
            return self.render_button()
        if self.type == 'checkbox':
            return self.render_checkbox()
        if self.type == 'file':
            return self.render_file()
        if self.type == 'password':
            return self.render_password()
        if self.type == 'radio':
            return self.render_radio()
        if self.type == 'select':
            return self.render_select()
        if self.type == 'signature':
            return self.render_signature()
        if self.type == 'text':
            return self.render_text()
        if self.type == 'textarea':
            return self.render_textarea()
        raise ValueError(f'Unknown input type: {self.type}')

    def render_style_attr_value(self):
        if self.style is None:
            return None
        return escape(';'.join([f"{key}:{value}" for key,value in self.style.items()]))
    
    def render_template_value_variable(self):
        """If this renderer is for a template type, returns the variable name that should contain the value of this field."""
        return ''

    def render_button(self):
        """Render a push button using the properties of this renderer"""
        return f""""""

    def render_checkbox(self):
        """Render a checkbox using the properties of this renderer"""
        return f"""<input type='checkbox' {self.render_basic_attrs()} {self.render_value_checked_if()}/>"""

    def render_file(self):
        """Render a file input using the properties of this renderer"""
        return f""""""

    def render_password(self):
        """Render a password input using the properties of this renderer"""
        return f"""<input type='password' {self.render_basic_attrs()} {self.render_value_attr()}/>"""

    def render_radio(self):
        """Render a radio button using the properties of this renderer"""
        return f"""<input type='radio' {self.render_basic_attrs()} {self.render_value_checked_if()}/>"""

    def render_select(self):
        """Render a select element using the properties of this renderer"""
        return f""""""

    def render_signature(self):
        """Render a signature field using the properties of this renderer"""
        return f"""<input type='file' data-real-type='signature' {self.render_basic_attrs()}/>"""

    def render_text(self):
        """Render a text field using the properties of this renderer"""
        return f"""<input type='text' {self.render_basic_attrs()} {self.render_value_attr()}/>"""

    def render_textarea(self):
        """Render a multiline text field using the properties of this renderer"""
        return f"""<textarea {self.render_basic_attrs()}>{self.render_value_content()}</textarea>"""

    def render_basic_attrs(self):
        """Render the basic attributes (name and style) to apply to the field, regardless of type."""
        return f"""name='{escape(self.name)}' style='{self.render_style_attr_value()}'"""
    
    def render_value_attr(self):
        """Render the value attribute of a field, or template code to generate such"""
        return ''
    
    def render_value_content(self):
        """Render the raw value of a field (e.g. for use in a textarea), or template code to generate such"""
        return ''
    
    def render_value_checked_if(self):
        """Render the 'checked' attribute for checkboxes or radio buttons, or template code to generate such"""
        return ''


class PHPFieldRenderer(FieldRenderer):
    def render_template_value_variable(self):
        return f"""$fd['{self.name}']"""
    
    def render_value_attr(self):
        return f"""<?=empty({self.render_template_value_variable()}) ? '' : 'value="'.htmlspecialchars({self.render_template_value_variable()}).'"'?>"""
    
    def render_value_content(self):
        return f"""<?=empty({self.render_template_value_variable()}) ? '' : htmlspecialchars({self.render_template_value_variable()})?>"""
    
    def render_value_checked_if(self):
        return f"""<?=empty({self.render_template_value_variable()}) ? '' : 'checked'?>"""


class JinjaFieldRenderer(FieldRenderer):
    def render_template_value_variable(self):
        return f"""fd['{self.name}']"""
    
    def render_value_attr(self):
        return f"""{{% if {self.render_template_value_variable()} %}}value='{{{{{self.render_template_value_variable()} | e}}}}'{{% endif %}}"""
    
    def render_value_content(self):
        return f"""{{% if {self.render_template_value_variable()} %}}{{{{{self.render_template_value_variable()} | e}}}}{{% endif %}}"""
    
    def render_value_checked_if(self):
        return f"""{{% if {self.render_template_value_variable()} %}}checked{{% endif %}}"""