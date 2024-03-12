# Importing necessary libraries and classes
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject, QgsLayerTreeLayer, QgsMapLayerType, QgsExpression, QgsFeatureRequest

# Import the dialog class
from .Attribute_dialog import AttributeDialog
from .config import COLUMN_NAME_1, COLUMN_NAME_2, COLUMN_NAME_3  # Import column names
import os.path


class Attribute:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.translator = self.init_translator()
        self.actions = []
        self.menu = self.tr(u'&AttributeFinder')
        self.first_start = True
        self.dlg = None

    def init_translator(self):
        """Initialize translator for localization."""
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'Attribute_{}.qm'.format(locale))
        translator = QTranslator()
        if os.path.exists(locale_path):
            translator.load(locale_path)
            QCoreApplication.installTranslator(translator)
        return translator

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('Attribute', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/Attribute/icon.png'
        self.add_action(icon_path, text=self.tr(u'AttributeFinder'), callback=self.run, parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&AttributeFinder'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work."""
        if self.first_start:
            self.dlg = AttributeDialog()
            self.first_start = False

        self.dlg.pushButton.clicked.connect(self.check_lineedit_text)
        self.dlg.pushButton_2.clicked.connect(self.clear_lineEdit)
        self.dlg.pushButton_3.clicked.connect(self.clicked_questionMark)

        root = QgsProject.instance().layerTreeRoot()
        layers = root.children()

        self.populate_combo_boxes(layers, COLUMN_NAME_1, COLUMN_NAME_2)

        self.dlg.show()
        result = self.dlg.exec_()

        if result:
            pass

    def populate_combo_boxes(self, layers, column_name1, column_name2):
        """Populate the combo boxes with unique values from specified columns."""
        self.dlg.comboBox.clear()
        self.dlg.comboBox2.clear()

        for layer_tree_layer in layers:
            if isinstance(layer_tree_layer, QgsLayerTreeLayer):
                layer = layer_tree_layer.layer()
                if layer and layer.type() == QgsMapLayerType.VectorLayer:
                    unique_values1 = set(feature[column_name1] for feature in layer.getFeatures())
                    unique_values2 = set(feature[column_name2] for feature in layer.getFeatures())

                    self.dlg.comboBox.addItems(sorted(unique_values1))
                    self.dlg.comboBox2.addItems(sorted(unique_values2))

    def clear_lineEdit(self):
        """Clear the line edit."""
        self.dlg.lineEdit.clear()

    def clicked_questionMark(self):
        """Display information message."""
        QMessageBox.information(None, '', '地番は全て半角で入力してください。', QMessageBox.Yes)

    def check_lineedit_text(self):
        """Check the line edit text."""
        lineedit_text = self.dlg.lineEdit.text()
        selected_value1 = self.dlg.comboBox.currentText()
        selected_value2 = self.dlg.comboBox2.currentText()

        layer = self.get_layer_by_attribute_values(selected_value1, selected_value2)
        if layer:
            self.zoom_to_features(layer, lineedit_text)

    def get_layer_by_attribute_values(self, value1, value2):
        """Get the layer based on the attribute values."""
        root = QgsProject.instance().layerTreeRoot()

        for layer_tree in root.children():
            if isinstance(layer_tree, QgsLayerTreeLayer):
                layer = layer_tree.layer()
                if layer:
                    if layer.dataProvider().dataSourceUri().find('.gpkg') != -1:
                        expr = QgsExpression("{} = '{}' AND {} = '{}'".format(COLUMN_NAME_1, value1, COLUMN_NAME_2, value2))
                        request = QgsFeatureRequest(expr)
                        features = layer.getFeatures(request)
                        if features:
                            return layer
        return None

    def zoom_to_features(self, layer, lineedit_text):
        """Zoom to the features based on line edit text."""
        if self.check_lineedit_data(layer, lineedit_text):
            expr = QgsExpression("{} = '{}'".format(COLUMN_NAME_3, lineedit_text))
            request = QgsFeatureRequest(expr)
            features = layer.getFeatures(request)
            for feature in features:
                bbox = feature.geometry().boundingBox()
                self.iface.mapCanvas().setExtent(bbox)
                self.iface.mapCanvas().refresh()
                break
        else:
            self.show_message("Line edit box data does not match the specified column.")

    def show_message(self, message):
        """Display a message."""
        msg_box = QMessageBox()
        msg_box.setText(message)
        msg_box.exec_()

    def check_lineedit_data(self, layer, lineedit_text):
        """Check line edit data."""
        if COLUMN_NAME_3 in layer.fields().names():
            expr = QgsExpression("{} = '{}'".format(COLUMN_NAME_3, lineedit_text))
            request = QgsFeatureRequest(expr)
            features = layer.getFeatures(request)
            return any(features)
        else:
            self.show_message("Column '{}' does not exist in the layer's attribute table.".format(COLUMN_NAME_3))
            return False
