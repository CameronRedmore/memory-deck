// Basic React component that renders a numeric input field

import React, { useState } from "react";
import {PanelSection, PanelSectionRow, gamepadDialogClasses, ButtonItem} from "decky-frontend-lib";

// NumericInputProps interface with value and onChange properties
interface NumericInputProps {
  label?: string = "Numeric Field";
  value: number;
  onChange: (value: string) => void;
  disabled?: boolean = false;
  min?: number = -Infinity;
  max?: number = Infinity;
  step: number = 1;
}

export const NumericInput = (props: NumericInputProps): JSX.Element => {
  const { label, value, onChange, min, max, disabled, step } = props;

  const [inputValue, setInputValue] = useState(value);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.valueAsNumber;
    setInputValue(newValue);
    onChange(newValue.toString());
  };

  const handleIncrement = (multiplier: number) => {
    const newValue = inputValue + (step * multiplier));
    if (newValue > max) {
      setInputValue(max);
      onChange(max.toString());
      return;
    }
    setInputValue(newValue);
    onChange(newValue.toString());
  };

  const handleDecrement = (multiplier: number) => {
    const newValue = inputValue - (step * multiplier);
    if (newValue < min) {
      setInputValue(min);
      onChange(min.toString());
      return;
    }
    setInputValue(newValue);
    onChange(newValue.toString());
  };

  const handleClear = () => {
    setInputValue(value);
    onChange(value.toString());
  };

  return (
    <PanelSection>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => handleDecrement(100)} disabled={disabled}>
          ---
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => handleDecrement(10)} disabled={disabled}>
          --
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => handleDecrement(1)} disabled={disabled}>
          -
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <input
          type="number"
          className={gamepadDialogClasses.FieldChildren}
          
          style={{ marginLeft: "calc(-1 * var(--field-negative-horizontal-margin))", marginRight: "calc(-1 * var(--field-negative-horizontal-margin))" }}
          value={inputValue}
          onChange={handleChange}
          min={min}
          max={max}
          step={step}
          disabled
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => handleIncrement(1)} disabled={disabled}>
          +
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => handleIncrement(10)} disabled={disabled}>
          ++
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => handleIncrement(100)} disabled={disabled}>
          +++
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}